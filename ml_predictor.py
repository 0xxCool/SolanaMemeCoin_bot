# ml_predictor.py
"""
Machine Learning Predictor für intelligente Token-Analyse
Verwendet Online Learning für kontinuierliche Verbesserung
"""
import numpy as np
import asyncio
import pickle
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import deque
import time
import json
from datetime import datetime, timedelta
import aiofiles
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
import pandas as pd
from scipy import stats

@dataclass
class TokenFeatures:
    """Features für ML Model"""
    # Basis Metriken
    liquidity_usd: float
    liquidity_change_5m: float
    market_cap: float
    age_minutes: float
    
    # Holder Metriken
    holder_count: int
    holder_growth_rate: float
    top_10_percentage: float
    distribution_score: float  # Gini coefficient
    
    # Volume Metriken
    volume_5m: float
    volume_1h: float
    volume_liquidity_ratio: float
    buy_sell_ratio: float
    
    # Price Action
    price_change_5m: float
    price_change_1h: float
    volatility: float
    momentum_score: float
    
    # Transaction Patterns
    tx_count_5m: int
    avg_tx_size: float
    large_tx_ratio: float  # Whale activity
    unique_traders: int
    
    # Technical Indicators
    rsi: float
    volume_weighted_price: float
    price_acceleration: float
    
    # Time Features
    hour_of_day: int
    day_of_week: int
    is_weekend: bool
    
    # Network Conditions
    network_congestion: float
    gas_price: float
    
    def to_array(self) -> np.ndarray:
        """Konvertiert zu NumPy Array für Model"""
        return np.array([
            self.liquidity_usd,
            self.liquidity_change_5m,
            self.market_cap,
            self.age_minutes,
            self.holder_count,
            self.holder_growth_rate,
            self.top_10_percentage,
            self.distribution_score,
            self.volume_5m,
            self.volume_1h,
            self.volume_liquidity_ratio,
            self.buy_sell_ratio,
            self.price_change_5m,
            self.price_change_1h,
            self.volatility,
            self.momentum_score,
            self.tx_count_5m,
            self.avg_tx_size,
            self.large_tx_ratio,
            self.unique_traders,
            self.rsi,
            self.volume_weighted_price,
            self.price_acceleration,
            self.hour_of_day,
            self.day_of_week,
            int(self.is_weekend),
            self.network_congestion,
            self.gas_price
        ])

@dataclass
class PredictionResult:
    """ML Prediction Ergebnis"""
    token_address: str
    predicted_return: float  # Erwartete Rendite in %
    confidence: float  # 0-1
    risk_score: float  # 0-1
    recommended_action: str  # BUY, HOLD, SKIP
    recommended_position_size: float  # in SOL
    predicted_peak_time: int  # Minuten bis zum Peak
    exit_indicators: List[str]
    
class MLPredictor:
    def __init__(self):
        self.models = {
            'returns': None,  # Predicts returns
            'risk': None,     # Predicts risk
            'timing': None    # Predicts optimal hold time
        }
        self.scaler = StandardScaler()
        self.feature_history = deque(maxlen=10000)
        self.prediction_history = deque(maxlen=1000)
        self.model_performance = {
            'accuracy': 0.0,
            'precision': 0.0,
            'profit_correlation': 0.0
        }
        
        # Model Paths
        self.model_dir = "ml_models"
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Online Learning Parameters
        self.retrain_threshold = 100  # Retrain after N new samples
        self.new_samples = []
        
        # Feature Importance Tracking
        self.feature_importance = {}
        
        # Initialize
        asyncio.create_task(self._initialize())
        
    async def _initialize(self):
        """Lädt oder trainiert Models"""
        try:
            # Versuche existierende Models zu laden
            await self.load_models()
            print("✅ ML Models geladen")
        except:
            # Trainiere neue Models mit Beispieldaten
            print("🔄 Trainiere neue ML Models...")
            await self.train_initial_models()
            
    async def predict(self, token_metrics: Dict) -> PredictionResult:
        """
        Hauptvorhersage-Funktion
        """
        try:
            # Extract Features
            features = await self._extract_features(token_metrics)
            feature_array = features.to_array().reshape(1, -1)
            
            # Scale Features
            feature_scaled = self.scaler.transform(feature_array)
            
            # Predictions von allen Models
            predicted_return = self.models['returns'].predict(feature_scaled)[0]
            risk_score = self.models['risk'].predict(feature_scaled)[0]
            optimal_hold_time = self.models['timing'].predict(feature_scaled)[0]
            
            # Calculate Confidence
            confidence = self._calculate_confidence(features, predicted_return)
            
            # Determine Action
            action = self._determine_action(predicted_return, risk_score, confidence)
            
            # Calculate Position Size mit Kelly Criterion
            position_size = self._calculate_position_size(
                predicted_return, risk_score, confidence
            )
            
            # Identify Exit Indicators
            exit_indicators = self._identify_exit_indicators(features)
            
            result = PredictionResult(
                token_address=token_metrics.get('address', ''),
                predicted_return=predicted_return,
                confidence=confidence,
                risk_score=risk_score,
                recommended_action=action,
                recommended_position_size=position_size,
                predicted_peak_time=int(optimal_hold_time),
                exit_indicators=exit_indicators
            )
            
            # Store for Online Learning
            self._store_prediction(features, result)
            
            return result
            
        except Exception as e:
            print(f"ML Prediction Error: {e}")
            # Fallback auf regelbasierte Prediction
            return self._fallback_prediction(token_metrics)
            
    async def _extract_features(self, metrics: Dict) -> TokenFeatures:
        """
        Extrahiert ML Features aus Token Metriken
        """
        now = datetime.now()
        
        # Calculate derived features
        liquidity = metrics.get('liquidity_usd', 0)
        volume = metrics.get('volume_usd_5m', 0)
        
        # Distribution Score (Gini Coefficient)
        distribution_score = self._calculate_gini_coefficient(
            metrics.get('holder_distribution', [])
        )
        
        # Momentum Score
        momentum = self._calculate_momentum(
            metrics.get('price_history', [])
        )
        
        # RSI
        rsi = self._calculate_rsi(
            metrics.get('price_history', [])
        )
        
        # Network Congestion (würde von RPC abgerufen)
        network_congestion = await self._get_network_congestion()
        
        return TokenFeatures(
            liquidity_usd=liquidity,
            liquidity_change_5m=metrics.get('liquidity_change_5m', 0),
            market_cap=metrics.get('market_cap_usd', 0),
            age_minutes=metrics.get('age_minutes', 0),
            holder_count=metrics.get('holder_count', 0),
            holder_growth_rate=metrics.get('holder_growth_rate', 0),
            top_10_percentage=metrics.get('top_10_percentage', 100),
            distribution_score=distribution_score,
            volume_5m=volume,
            volume_1h=metrics.get('volume_usd_1h', 0),
            volume_liquidity_ratio=volume / max(liquidity, 1),
            buy_sell_ratio=metrics.get('buy_sell_ratio', 1),
            price_change_5m=metrics.get('price_change_5m', 0),
            price_change_1h=metrics.get('price_change_1h', 0),
            volatility=metrics.get('volatility', 0),
            momentum_score=momentum,
            tx_count_5m=metrics.get('tx_count_5m', 0),
            avg_tx_size=metrics.get('avg_tx_size', 0),
            large_tx_ratio=metrics.get('large_tx_ratio', 0),
            unique_traders=metrics.get('unique_traders', 0),
            rsi=rsi,
            volume_weighted_price=metrics.get('vwap', 0),
            price_acceleration=metrics.get('price_acceleration', 0),
            hour_of_day=now.hour,
            day_of_week=now.weekday(),
            is_weekend=now.weekday() >= 5,
            network_congestion=network_congestion,
            gas_price=metrics.get('gas_price', 5000)
        )
        
    def _calculate_confidence(self, features: TokenFeatures, 
                            predicted_return: float) -> float:
        """
        Berechnet Confidence Score basierend auf Feature Quality
        """
        confidence = 0.5  # Base confidence
        
        # Adjust based on data quality
        if features.holder_count > 100:
            confidence += 0.1
        if features.volume_5m > 10000:
            confidence += 0.1
        if features.liquidity_usd > 20000:
            confidence += 0.1
        if abs(features.buy_sell_ratio - 1) < 0.2:  # Balanced buying/selling
            confidence += 0.1
        if features.age_minutes > 5 and features.age_minutes < 60:
            confidence += 0.1
            
        # Penalize for red flags
        if features.top_10_percentage > 50:
            confidence -= 0.2
        if features.distribution_score > 0.8:  # High inequality
            confidence -= 0.1
            
        # Model-specific confidence
        if hasattr(self.models['returns'], 'predict_proba'):
            try:
                proba = self.models['returns'].predict_proba([[predicted_return]])
                model_confidence = np.max(proba)
                confidence = (confidence + model_confidence) / 2
            except:
                pass
                
        return np.clip(confidence, 0, 1)
        
    def _determine_action(self, predicted_return: float, 
                         risk_score: float, confidence: float) -> str:
        """
        Bestimmt empfohlene Aktion
        """
        # Risk-adjusted return
        risk_adjusted = predicted_return * (1 - risk_score)
        
        if confidence < 0.3:
            return "SKIP"
        
        if risk_adjusted > 50 and confidence > 0.7:
            return "BUY_STRONG"
        elif risk_adjusted > 20 and confidence > 0.5:
            return "BUY"
        elif risk_adjusted > 10 and risk_score < 0.3:
            return "BUY_SMALL"
        else:
            return "SKIP"
            
    def _calculate_position_size(self, predicted_return: float,
                                risk_score: float, confidence: float) -> float:
        """
        Berechnet optimale Position Size mit Kelly Criterion
        """
        # Kelly Formula angepasst für Crypto
        win_prob = confidence
        loss_prob = 1 - confidence
        win_amount = predicted_return / 100  # Convert to decimal
        loss_amount = risk_score
        
        if loss_amount == 0:
            loss_amount = 0.1  # Minimum loss assumption
            
        kelly_fraction = (win_prob * win_amount - loss_prob * loss_amount) / win_amount
        
        # Conservative Kelly (25% of full Kelly)
        conservative_kelly = kelly_fraction * 0.25
        
        # Apply bounds
        position_size = np.clip(conservative_kelly, 0.01, 0.5)
        
        # Further adjust based on confidence
        if confidence < 0.5:
            position_size *= 0.5
        elif confidence > 0.8:
            position_size *= 1.2
            
        return round(position_size, 3)
        
    def _identify_exit_indicators(self, features: TokenFeatures) -> List[str]:
        """
        Identifiziert Signale für Exit
        """
        indicators = []
        
        if features.volume_liquidity_ratio < 0.1:
            indicators.append("LOW_VOLUME")
        if features.holder_growth_rate < -10:
            indicators.append("HOLDER_DECLINE")
        if features.momentum_score < -20:
            indicators.append("MOMENTUM_LOSS")
        if features.rsi > 80:
            indicators.append("OVERBOUGHT")
        if features.large_tx_ratio > 0.5:
            indicators.append("WHALE_ACTIVITY")
            
        return indicators
        
    def _calculate_gini_coefficient(self, distribution: List[float]) -> float:
        """
        Berechnet Gini Coefficient für Holder Distribution
        """
        if not distribution:
            return 1.0
            
        sorted_dist = sorted(distribution)
        n = len(sorted_dist)
        cumsum = np.cumsum(sorted_dist)
        
        return (2 * np.sum((np.arange(1, n+1) * sorted_dist))) / (n * cumsum[-1]) - (n + 1) / n
        
    def _calculate_momentum(self, price_history: List[float]) -> float:
        """
        Berechnet Price Momentum
        """
        if len(price_history) < 2:
            return 0
            
        # Rate of Change
        roc = ((price_history[-1] - price_history[0]) / price_history[0]) * 100
        
        # Smooth momentum with moving average
        if len(price_history) > 5:
            ma5 = np.mean(price_history[-5:])
            ma10 = np.mean(price_history[-10:]) if len(price_history) > 10 else ma5
            momentum = ((ma5 - ma10) / ma10) * 100
            return (roc + momentum) / 2
            
        return roc
        
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """
        Berechnet Relative Strength Index
        """
        if len(prices) < period:
            return 50  # Neutral RSI
            
        deltas = np.diff(prices)
        gains = deltas[deltas > 0]
        losses = -deltas[deltas < 0]
        
        avg_gain = np.mean(gains) if len(gains) > 0 else 0
        avg_loss = np.mean(losses) if len(losses) > 0 else 0.001
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
        
    async def _get_network_congestion(self) -> float:
        """
        Ermittelt aktuelle Netzwerk-Auslastung
        """
        # Würde von RPC abgerufen
        # Placeholder: Random zwischen 0 und 1
        return 0.5
        
    def _store_prediction(self, features: TokenFeatures, result: PredictionResult):
        """
        Speichert Prediction für Online Learning
        """
        self.prediction_history.append({
            'timestamp': time.time(),
            'features': asdict(features),
            'prediction': asdict(result)
        })
        
    async def update_with_outcome(self, token_address: str, 
                                 actual_return: float, actual_hold_time: int):
        """
        Aktualisiert Model mit tatsächlichem Outcome
        """
        # Finde entsprechende Prediction
        for pred in self.prediction_history:
            if pred['prediction']['token_address'] == token_address:
                # Füge Outcome hinzu
                pred['actual_return'] = actual_return
                pred['actual_hold_time'] = actual_hold_time
                
                # Füge zu Training Samples hinzu
                self.new_samples.append(pred)
                
                # Retrain wenn genug neue Samples
                if len(self.new_samples) >= self.retrain_threshold:
                    await self.retrain_models()
                    
                break
                
    async def retrain_models(self):
        """
        Online Learning - Retraining mit neuen Daten
        """
        print("🔄 Retraining ML Models mit neuen Daten...")
        
        try:
            # Konvertiere zu Training Data
            X = []
            y_returns = []
            y_risk = []
            y_timing = []
            
            for sample in self.new_samples:
                features = TokenFeatures(**sample['features'])
                X.append(features.to_array())
                y_returns.append(sample['actual_return'])
                y_risk.append(1 if sample['actual_return'] < -10 else 0)  # Risk indicator
                y_timing.append(sample['actual_hold_time'])
                
            X = np.array(X)
            
            # Incremental Learning
            if hasattr(self.models['returns'], 'partial_fit'):
                # Für SGD-basierte Models
                self.models['returns'].partial_fit(X, y_returns)
                self.models['risk'].partial_fit(X, y_risk)
                self.models['timing'].partial_fit(X, y_timing)
            else:
                # Für Tree-basierte Models: Combine mit alten Daten und retrain
                # Lade alte Training Data
                old_X, old_y = await self._load_training_data()
                
                if old_X is not None:
                    X = np.vstack([old_X, X])
                    y_returns = np.concatenate([old_y['returns'], y_returns])
                    y_risk = np.concatenate([old_y['risk'], y_risk])
                    y_timing = np.concatenate([old_y['timing'], y_timing])
                    
                # Retrain
                self.models['returns'].fit(self.scaler.fit_transform(X), y_returns)
                self.models['risk'].fit(self.scaler.transform(X), y_risk)
                self.models['timing'].fit(self.scaler.transform(X), y_timing)
                
            # Update Feature Importance
            self._update_feature_importance()
            
            # Save Updated Models
            await self.save_models()
            
            # Clear new samples
            self.new_samples = []
            
            print("✅ Models erfolgreich aktualisiert")
            
        except Exception as e:
            print(f"Retraining Error: {e}")
            
    def _update_feature_importance(self):
        """
        Aktualisiert Feature Importance Scores
        """
        if hasattr(self.models['returns'], 'feature_importances_'):
            feature_names = [
                'liquidity_usd', 'liquidity_change_5m', 'market_cap', 'age_minutes',
                'holder_count', 'holder_growth_rate', 'top_10_percentage', 'distribution_score',
                'volume_5m', 'volume_1h', 'volume_liquidity_ratio', 'buy_sell_ratio',
                'price_change_5m', 'price_change_1h', 'volatility', 'momentum_score',
                'tx_count_5m', 'avg_tx_size', 'large_tx_ratio', 'unique_traders',
                'rsi', 'volume_weighted_price', 'price_acceleration',
                'hour_of_day', 'day_of_week', 'is_weekend', 'network_congestion', 'gas_price'
            ]
            
            importances = self.models['returns'].feature_importances_
            self.feature_importance = dict(zip(feature_names, importances))
            
            # Print Top 10 Features
            top_features = sorted(self.feature_importance.items(), 
                                key=lambda x: x[1], reverse=True)[:10]
            print("\n📊 Top 10 Important Features:")
            for name, importance in top_features:
                print(f"  - {name}: {importance:.3f}")
                
    async def train_initial_models(self):
        """
        Trainiert initiale Models mit synthetischen Daten
        """
        # Generate synthetic training data
        n_samples = 1000
        X = np.random.randn(n_samples, 28)  # 28 features
        
        # Synthetic targets mit realistischen Patterns
        y_returns = np.random.normal(20, 50, n_samples)  # Returns centered at 20%
        y_risk = (y_returns < -10).astype(int)  # Risk wenn Return < -10%
        y_timing = np.random.exponential(30, n_samples)  # Hold time in minutes
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train Models
        self.models['returns'] = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42,
            subsample=0.8
        )
        
        self.models['risk'] = RandomForestRegressor(
            n_estimators=100,
            max_depth=5,
            random_state=42
        )
        
        self.models['timing'] = RandomForestRegressor(
            n_estimators=50,
            max_depth=3,
            random_state=42
        )
        
        # Fit models
        self.models['returns'].fit(X_scaled, y_returns)
        self.models['risk'].fit(X_scaled, y_risk)
        self.models['timing'].fit(X_scaled, y_timing)
        
        # Save models
        await self.save_models()
        
        print("✅ Initial models trained")
        
    async def save_models(self):
        """
        Speichert Models auf Disk
        """
        try:
            # Save models
            joblib.dump(self.models['returns'], f"{self.model_dir}/returns_model.pkl")
            joblib.dump(self.models['risk'], f"{self.model_dir}/risk_model.pkl")
            joblib.dump(self.models['timing'], f"{self.model_dir}/timing_model.pkl")
            joblib.dump(self.scaler, f"{self.model_dir}/scaler.pkl")
            
            # Save metadata
            metadata = {
                'version': '2.0',
                'last_update': datetime.now().isoformat(),
                'feature_importance': self.feature_importance,
                'model_performance': self.model_performance,
                'sample_count': len(self.feature_history)
            }
            
            async with aiofiles.open(f"{self.model_dir}/metadata.json", 'w') as f:
                await f.write(json.dumps(metadata, indent=2))
                
        except Exception as e:
            print(f"Model Save Error: {e}")
            
    async def load_models(self):
        """
        Lädt Models von Disk
        """
        self.models['returns'] = joblib.load(f"{self.model_dir}/returns_model.pkl")
        self.models['risk'] = joblib.load(f"{self.model_dir}/risk_model.pkl")
        self.models['timing'] = joblib.load(f"{self.model_dir}/timing_model.pkl")
        self.scaler = joblib.load(f"{self.model_dir}/scaler.pkl")
        
        # Load metadata
        async with aiofiles.open(f"{self.model_dir}/metadata.json", 'r') as f:
            metadata = json.loads(await f.read())
            self.feature_importance = metadata.get('feature_importance', {})
            self.model_performance = metadata.get('model_performance', {})
            
    async def _load_training_data(self) -> Tuple[Optional[np.ndarray], Optional[Dict]]:
        """
        Lädt gespeicherte Training Data
        """
        try:
            # Würde von Disk/Database geladen
            return None, None
        except:
            return None, None
            
    def _fallback_prediction(self, metrics: Dict) -> PredictionResult:
        """
        Fallback wenn ML fehlschlägt
        """
        # Regelbasierte Prediction
        score = metrics.get('score', 50)
        
        if score > 80:
            action = "BUY"
            position = 0.1
            predicted_return = 30
        elif score > 70:
            action = "BUY_SMALL"
            position = 0.05
            predicted_return = 15
        else:
            action = "SKIP"
            position = 0
            predicted_return = 0
            
        return PredictionResult(
            token_address=metrics.get('address', ''),
            predicted_return=predicted_return,
            confidence=0.3,  # Low confidence für fallback
            risk_score=0.5,
            recommended_action=action,
            recommended_position_size=position,
            predicted_peak_time=30,
            exit_indicators=[]
        )
        
    async def get_model_performance(self) -> Dict:
        """
        Gibt Model Performance Metrics zurück
        """
        if len(self.prediction_history) < 10:
            return self.model_performance
            
        # Calculate performance metrics
        predictions_with_outcome = [
            p for p in self.prediction_history 
            if 'actual_return' in p
        ]
        
        if predictions_with_outcome:
            predicted = [p['prediction']['predicted_return'] for p in predictions_with_outcome]
            actual = [p['actual_return'] for p in predictions_with_outcome]
            
            # Correlation
            if len(predicted) > 1:
                correlation = np.corrcoef(predicted, actual)[0, 1]
                self.model_performance['profit_correlation'] = correlation
                
            # Accuracy (within 20% error)
            accurate = sum(
                1 for p, a in zip(predicted, actual)
                if abs(p - a) / max(abs(a), 1) < 0.2
            )
            self.model_performance['accuracy'] = accurate / len(predicted)
            
            # Directional Accuracy
            direction_correct = sum(
                1 for p, a in zip(predicted, actual)
                if (p > 0 and a > 0) or (p <= 0 and a <= 0)
            )
            self.model_performance['direction_accuracy'] = direction_correct / len(predicted)
            
        return self.model_performance

# Global Instance
ml_predictor = MLPredictor()

# Public API
async def predict_token_performance(token_metrics: Dict) -> PredictionResult:
    """Public API für Token Prediction"""
    return await ml_predictor.predict(token_metrics)

async def update_model_with_outcome(token_address: str, 
                                   actual_return: float, 
                                   actual_hold_time: int):
    """Update Model mit tatsächlichem Ergebnis"""
    await ml_predictor.update_with_outcome(token_address, actual_return, actual_hold_time)

async def get_feature_importance() -> Dict:
    """Gibt Feature Importance zurück"""
    return ml_predictor.feature_importance

async def get_model_stats() -> Dict:
    """Gibt Model Performance Stats zurück"""
    return await ml_predictor.get_model_performance()