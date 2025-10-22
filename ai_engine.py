# ai_engine.py
"""
Advanced AI Engine with Neural Networks, Reinforcement Learning & Self-Learning
State-of-the-art ML for maximum trading performance
"""
import os
import asyncio
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import pickle
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from collections import deque
import time
import json
from datetime import datetime
import aiofiles
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
import joblib

# ============================================================================
# NEURAL NETWORK ARCHITECTURES
# ============================================================================

class TokenPricePredictor(nn.Module):
    """
    Deep Neural Network for Token Price Prediction
    Architecture: Multi-layer LSTM + Attention + Dense
    """
    def __init__(self, input_size: int = 50, hidden_size: int = 128,
                 num_layers: int = 3, dropout: float = 0.3):
        super(TokenPricePredictor, self).__init__()

        # LSTM layers for sequential pattern learning
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            batch_first=True,
            bidirectional=True
        )

        # Attention mechanism
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_size * 2,
            num_heads=4,
            dropout=dropout
        )

        # Dense layers
        self.fc1 = nn.Linear(hidden_size * 2, 256)
        self.fc2 = nn.Linear(256, 128)
        self.fc3 = nn.Linear(128, 64)
        self.output = nn.Linear(64, 3)  # [predicted_return, confidence, risk]

        self.dropout = nn.Dropout(dropout)
        self.relu = nn.ReLU()
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        # LSTM processing
        lstm_out, (h_n, c_n) = self.lstm(x)

        # Attention
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)

        # Take last output
        x = attn_out[:, -1, :]

        # Dense layers with residual connections
        x1 = self.dropout(self.relu(self.fc1(x)))
        x2 = self.dropout(self.relu(self.fc2(x1)))
        x3 = self.dropout(self.relu(self.fc3(x2)))

        # Output: [return%, confidence, risk]
        output = self.output(x3)

        return output


class RiskAssessmentNetwork(nn.Module):
    """
    Deep Network for Risk Assessment
    Specialized in detecting scams, rugs, and high-risk tokens
    """
    def __init__(self, input_size: int = 40):
        super(RiskAssessmentNetwork, self).__init__()

        self.fc1 = nn.Linear(input_size, 256)
        self.fc2 = nn.Linear(256, 128)
        self.fc3 = nn.Linear(128, 64)
        self.fc4 = nn.Linear(64, 32)
        self.output = nn.Linear(32, 5)  # [rug_prob, honeypot_prob, dump_prob, safe_prob, quality_score]

        self.batch_norm1 = nn.BatchNorm1d(256)
        self.batch_norm2 = nn.BatchNorm1d(128)
        self.batch_norm3 = nn.BatchNorm1d(64)

        self.dropout = nn.Dropout(0.3)
        self.relu = nn.ReLU()
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = self.relu(self.batch_norm1(self.fc1(x)))
        x = self.dropout(x)
        x = self.relu(self.batch_norm2(self.fc2(x)))
        x = self.dropout(x)
        x = self.relu(self.batch_norm3(self.fc3(x)))
        x = self.dropout(x)
        x = self.relu(self.fc4(x))
        x = self.sigmoid(self.output(x))

        return x


class TradingStrategyDQN(nn.Module):
    """
    Deep Q-Network for Reinforcement Learning
    Learns optimal trading strategies through experience
    """
    def __init__(self, state_size: int = 60, action_size: int = 5):
        super(TradingStrategyDQN, self).__init__()

        # State: [token_features, portfolio_state, market_conditions]
        # Actions: [buy_small, buy_medium, buy_large, sell_partial, sell_all]

        self.fc1 = nn.Linear(state_size, 256)
        self.fc2 = nn.Linear(256, 256)
        self.fc3 = nn.Linear(256, 128)

        # Dueling DQN architecture
        self.value_stream = nn.Linear(128, 64)
        self.value = nn.Linear(64, 1)

        self.advantage_stream = nn.Linear(128, 64)
        self.advantage = nn.Linear(64, action_size)

        self.relu = nn.ReLU()

    def forward(self, state):
        x = self.relu(self.fc1(state))
        x = self.relu(self.fc2(x))
        x = self.relu(self.fc3(x))

        # Dueling streams
        value = self.relu(self.value_stream(x))
        value = self.value(value)

        advantage = self.relu(self.advantage_stream(x))
        advantage = self.advantage(advantage)

        # Combine: Q(s,a) = V(s) + (A(s,a) - mean(A(s,a)))
        q_values = value + (advantage - advantage.mean(dim=1, keepdim=True))

        return q_values


# ============================================================================
# REINFORCEMENT LEARNING AGENT
# ============================================================================

@dataclass
class Experience:
    """Experience tuple for replay buffer"""
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool


class ReplayBuffer:
    """Experience Replay Buffer for RL"""
    def __init__(self, capacity: int = 10000):
        self.buffer = deque(maxlen=capacity)

    def push(self, experience: Experience):
        self.buffer.append(experience)

    def sample(self, batch_size: int) -> List[Experience]:
        indices = np.random.choice(len(self.buffer), batch_size, replace=False)
        return [self.buffer[i] for i in indices]

    def __len__(self):
        return len(self.buffer)


class TradingAgent:
    """
    Reinforcement Learning Agent for Trading
    Uses DQN with experience replay and target network
    """
    def __init__(self, state_size: int = 60, action_size: int = 5):
        self.state_size = state_size
        self.action_size = action_size

        # Hyperparameters
        self.gamma = 0.99  # Discount factor
        self.epsilon = 1.0  # Exploration rate
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = 0.0001
        self.batch_size = 64

        # Networks
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.policy_net = TradingStrategyDQN(state_size, action_size).to(self.device)
        self.target_net = TradingStrategyDQN(state_size, action_size).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        # Optimizer
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=self.learning_rate)

        # Replay buffer
        self.replay_buffer = ReplayBuffer(capacity=50000)

        # Stats
        self.total_steps = 0
        self.episodes = 0

    def select_action(self, state: np.ndarray, training: bool = True) -> int:
        """
        Select action using epsilon-greedy policy
        """
        if training and np.random.rand() < self.epsilon:
            return np.random.randint(self.action_size)

        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.policy_net(state_tensor)
            return q_values.argmax().item()

    def store_experience(self, state, action, reward, next_state, done):
        """Store experience in replay buffer"""
        exp = Experience(state, action, reward, next_state, done)
        self.replay_buffer.push(exp)

    def train_step(self):
        """Perform one training step"""
        if len(self.replay_buffer) < self.batch_size:
            return 0

        # Sample batch
        batch = self.replay_buffer.sample(self.batch_size)

        # Prepare tensors
        states = torch.FloatTensor([e.state for e in batch]).to(self.device)
        actions = torch.LongTensor([e.action for e in batch]).to(self.device)
        rewards = torch.FloatTensor([e.reward for e in batch]).to(self.device)
        next_states = torch.FloatTensor([e.next_state for e in batch]).to(self.device)
        dones = torch.FloatTensor([e.done for e in batch]).to(self.device)

        # Current Q values
        current_q = self.policy_net(states).gather(1, actions.unsqueeze(1))

        # Target Q values (Double DQN)
        with torch.no_grad():
            next_actions = self.policy_net(next_states).argmax(1)
            next_q = self.target_net(next_states).gather(1, next_actions.unsqueeze(1))
            target_q = rewards.unsqueeze(1) + (1 - dones.unsqueeze(1)) * self.gamma * next_q

        # Loss
        loss = nn.MSELoss()(current_q, target_q)

        # Optimize
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.optimizer.step()

        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        self.total_steps += 1

        # Update target network
        if self.total_steps % 100 == 0:
            self.target_net.load_state_dict(self.policy_net.state_dict())

        return loss.item()


# ============================================================================
# ADVANCED AI ENGINE
# ============================================================================

class AdvancedAIEngine:
    """
    Complete AI Engine combining all ML models
    Self-learning, adaptive, and continuously improving
    """
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"🤖 AI Engine using device: {self.device}")

        # Neural Networks
        self.price_predictor = TokenPricePredictor().to(self.device)
        self.risk_assessor = RiskAssessmentNetwork().to(self.device)

        # Reinforcement Learning Agent
        self.trading_agent = TradingAgent()

        # Traditional ML (ensemble)
        self.ensemble_models = {
            'gb_regressor': GradientBoostingRegressor(n_estimators=100),
            'rf_regressor': RandomForestRegressor(n_estimators=100)
        }

        # Scalers
        self.feature_scaler = RobustScaler()
        self.price_scaler = StandardScaler()

        # Training data
        self.training_data = []
        self.validation_data = []

        # Performance tracking
        self.performance_metrics = {
            'predictions': 0,
            'correct_direction': 0,
            'avg_error': 0,
            'sharpe_ratio': 0,
            'total_profit': 0
        }

        # Model paths
        self.model_dir = "ai_models"
        os.makedirs(self.model_dir, exist_ok=True)

        # Load existing models if available
        asyncio.create_task(self.load_models())

        # Training scheduler
        self.last_training = time.time()
        self.training_interval = 3600  # Retrain every hour

    async def load_models(self):
        """Load pre-trained models"""
        try:
            # Load neural networks
            price_path = f"{self.model_dir}/price_predictor.pth"
            if os.path.exists(price_path):
                self.price_predictor.load_state_dict(torch.load(price_path, map_location=self.device))
                print("✅ Loaded Price Predictor")

            risk_path = f"{self.model_dir}/risk_assessor.pth"
            if os.path.exists(risk_path):
                self.risk_assessor.load_state_dict(torch.load(risk_path, map_location=self.device))
                print("✅ Loaded Risk Assessor")

            # Load RL agent
            agent_path = f"{self.model_dir}/trading_agent.pth"
            if os.path.exists(agent_path):
                self.trading_agent.policy_net.load_state_dict(torch.load(agent_path, map_location=self.device))
                self.trading_agent.target_net.load_state_dict(self.trading_agent.policy_net.state_dict())
                print("✅ Loaded Trading Agent")

            # Load ensemble models
            for name, model in self.ensemble_models.items():
                path = f"{self.model_dir}/{name}.pkl"
                if os.path.exists(path):
                    self.ensemble_models[name] = joblib.load(path)
                    print(f"✅ Loaded {name}")

            # Load scalers
            scaler_path = f"{self.model_dir}/scalers.pkl"
            if os.path.exists(scaler_path):
                scalers = joblib.load(scaler_path)
                self.feature_scaler = scalers['feature']
                self.price_scaler = scalers['price']
                print("✅ Loaded Scalers")

        except Exception as e:
            print(f"⚠️ Model loading warning: {e}")
            print("📝 Starting with fresh models")

    async def save_models(self):
        """Save all models"""
        try:
            # Save neural networks
            torch.save(self.price_predictor.state_dict(), f"{self.model_dir}/price_predictor.pth")
            torch.save(self.risk_assessor.state_dict(), f"{self.model_dir}/risk_assessor.pth")
            torch.save(self.trading_agent.policy_net.state_dict(), f"{self.model_dir}/trading_agent.pth")

            # Save ensemble models
            for name, model in self.ensemble_models.items():
                joblib.dump(model, f"{self.model_dir}/{name}.pkl")

            # Save scalers
            scalers = {
                'feature': self.feature_scaler,
                'price': self.price_scaler
            }
            joblib.dump(scalers, f"{self.model_dir}/scalers.pkl")

            # Save metadata
            metadata = {
                'last_save': datetime.now().isoformat(),
                'performance': self.performance_metrics,
                'training_samples': len(self.training_data),
                'agent_steps': self.trading_agent.total_steps
            }

            async with aiofiles.open(f"{self.model_dir}/metadata.json", 'w') as f:
                await f.write(json.dumps(metadata, indent=2))

            print("✅ Models saved successfully")

        except Exception as e:
            print(f"❌ Error saving models: {e}")

    async def predict_token_performance(self, token_data: Dict) -> Dict:
        """
        Complete prediction using all models
        Returns comprehensive analysis and recommendation
        """
        # Extract and prepare features
        features = await self._extract_features(token_data)

        # Neural Network predictions
        nn_prediction = await self._neural_network_predict(features)

        # Risk assessment
        risk_analysis = await self._assess_risk(features)

        # RL agent recommendation
        rl_action = await self._get_rl_recommendation(features, token_data)

        # Ensemble predictions
        ensemble_prediction = await self._ensemble_predict(features)

        # Combine all predictions (weighted ensemble)
        final_prediction = self._combine_predictions(
            nn_prediction,
            ensemble_prediction,
            risk_analysis,
            rl_action
        )

        return final_prediction

    async def _extract_features(self, token_data: Dict) -> np.ndarray:
        """Extract features from token data"""
        features = []

        # Basic metrics (normalized)
        features.extend([
            np.log1p(token_data.get('liquidity_usd', 1)),
            token_data.get('age_minutes', 0) / 60,
            np.log1p(token_data.get('holder_count', 1)),
            token_data.get('top_10_percentage', 100) / 100,
            np.log1p(token_data.get('volume_usd_5m', 1)),
            token_data.get('price_change_5m', 0) / 100,
            token_data.get('buy_sell_ratio', 1),
            token_data.get('tx_count_5m', 0) / 100,
        ])

        # Advanced features
        features.extend([
            token_data.get('volatility', 0),
            token_data.get('momentum_score', 0) / 100,
            token_data.get('distribution_gini', 0.5),
            token_data.get('whale_concentration', 0),
        ])

        # Time features
        now = datetime.now()
        features.extend([
            now.hour / 24,
            now.weekday() / 7,
            int(now.weekday() >= 5),  # Weekend
        ])

        return np.array(features, dtype=np.float32)

    async def _neural_network_predict(self, features: np.ndarray) -> Dict:
        """Price prediction using neural network"""
        self.price_predictor.eval()

        with torch.no_grad():
            # Prepare input (add sequence dimension)
            x = torch.FloatTensor(features).unsqueeze(0).unsqueeze(0).to(self.device)

            # Predict
            output = self.price_predictor(x)

            predicted_return = output[0, 0].item()
            confidence = output[0, 1].item()
            risk = output[0, 2].item()

        return {
            'predicted_return': predicted_return,
            'confidence': confidence,
            'risk': risk,
            'source': 'neural_network'
        }

    async def _assess_risk(self, features: np.ndarray) -> Dict:
        """Comprehensive risk assessment"""
        self.risk_assessor.eval()

        with torch.no_grad():
            x = torch.FloatTensor(features).unsqueeze(0).to(self.device)
            output = self.risk_assessor(x)

            rug_prob = output[0, 0].item()
            honeypot_prob = output[0, 1].item()
            dump_prob = output[0, 2].item()
            safe_prob = output[0, 3].item()
            quality_score = output[0, 4].item()

        # Overall risk score (0-1, higher = more risky)
        overall_risk = (rug_prob * 0.4 + honeypot_prob * 0.3 + dump_prob * 0.3)

        return {
            'rug_probability': rug_prob,
            'honeypot_probability': honeypot_prob,
            'dump_probability': dump_prob,
            'safe_probability': safe_prob,
            'quality_score': quality_score,
            'overall_risk': overall_risk,
            'risk_level': 'HIGH' if overall_risk > 0.7 else 'MEDIUM' if overall_risk > 0.4 else 'LOW'
        }

    async def _get_rl_recommendation(self, features: np.ndarray, token_data: Dict) -> Dict:
        """Get recommendation from RL agent"""
        # Build state (features + portfolio state)
        state = features  # Simplified, would include portfolio in production

        # Get action
        action = self.trading_agent.select_action(state, training=False)

        # Action mapping
        actions = ['buy_small', 'buy_medium', 'buy_large', 'sell_partial', 'sell_all']

        return {
            'recommended_action': actions[action],
            'action_index': action,
            'source': 'reinforcement_learning'
        }

    async def _ensemble_predict(self, features: np.ndarray) -> Dict:
        """Ensemble prediction from traditional ML"""
        predictions = []

        for name, model in self.ensemble_models.items():
            try:
                if hasattr(model, 'predict'):
                    pred = model.predict(features.reshape(1, -1))[0]
                    predictions.append(pred)
            except:
                pass

        if predictions:
            avg_prediction = np.mean(predictions)
            std_prediction = np.std(predictions)
        else:
            avg_prediction = 0
            std_prediction = 0

        return {
            'predicted_return': avg_prediction,
            'uncertainty': std_prediction,
            'source': 'ensemble'
        }

    def _combine_predictions(self, nn_pred: Dict, ensemble_pred: Dict,
                            risk_analysis: Dict, rl_action: Dict) -> Dict:
        """Combine all predictions into final recommendation"""

        # Weighted average of predictions
        nn_weight = 0.4
        ensemble_weight = 0.3
        rl_weight = 0.3

        final_return = (
            nn_pred['predicted_return'] * nn_weight +
            ensemble_pred['predicted_return'] * ensemble_weight
        )

        # Adjust for risk
        risk_adjusted_return = final_return * (1 - risk_analysis['overall_risk'])

        # Determine action
        if risk_analysis['overall_risk'] > 0.7:
            action = 'SKIP'
            buy_amount = 0
        elif risk_adjusted_return > 50 and risk_analysis['safe_probability'] > 0.7:
            action = 'BUY_LARGE'
            buy_amount = 0.2
        elif risk_adjusted_return > 30:
            action = 'BUY_MEDIUM'
            buy_amount = 0.1
        elif risk_adjusted_return > 15:
            action = 'BUY_SMALL'
            buy_amount = 0.05
        else:
            action = 'SKIP'
            buy_amount = 0

        # Confidence calculation
        confidence = (
            nn_pred['confidence'] * 0.4 +
            (1 - risk_analysis['overall_risk']) * 0.3 +
            risk_analysis['safe_probability'] * 0.3
        )

        return {
            'recommended_action': action,
            'buy_amount_sol': buy_amount,
            'predicted_return': final_return,
            'risk_adjusted_return': risk_adjusted_return,
            'confidence': confidence,
            'risk_analysis': risk_analysis,
            'rl_suggestion': rl_action['recommended_action'],
            'component_predictions': {
                'neural_network': nn_pred,
                'ensemble': ensemble_pred,
                'reinforcement_learning': rl_action
            }
        }

    async def learn_from_trade(self, token_data: Dict, action: str,
                              actual_return: float, trade_duration: int):
        """
        Continuous learning from each trade
        Updates all models based on outcome
        """
        # Extract features
        features = await self._extract_features(token_data)

        # Store training data
        self.training_data.append({
            'features': features,
            'action': action,
            'return': actual_return,
            'duration': trade_duration,
            'timestamp': time.time()
        })

        # RL agent learning
        if len(self.training_data) > 1:
            prev_trade = self.training_data[-2]

            # Calculate reward (profit/loss)
            reward = actual_return / 100  # Normalize to -1 to 1 range

            # Store experience
            state = prev_trade['features']
            action_idx = self._action_to_index(prev_trade['action'])
            next_state = features
            done = True  # Trade completed

            self.trading_agent.store_experience(state, action_idx, reward, next_state, done)

            # Train if enough experiences
            if len(self.trading_agent.replay_buffer) >= 64:
                for _ in range(4):  # Multiple training steps
                    self.trading_agent.train_step()

        # Update performance metrics
        self.performance_metrics['predictions'] += 1
        if (actual_return > 0 and action.startswith('BUY')) or \
           (actual_return < 0 and action == 'SKIP'):
            self.performance_metrics['correct_direction'] += 1

        # Periodic retraining
        if time.time() - self.last_training > self.training_interval:
            asyncio.create_task(self.retrain_models())
            self.last_training = time.time()

        # Save models periodically
        if len(self.training_data) % 50 == 0:
            await self.save_models()

    def _action_to_index(self, action: str) -> int:
        """Convert action string to index"""
        actions = {
            'BUY_SMALL': 0,
            'BUY_MEDIUM': 1,
            'BUY_LARGE': 2,
            'SELL_PARTIAL': 3,
            'SELL_ALL': 4,
            'SKIP': 0  # Default to buy_small for unknown
        }
        return actions.get(action, 0)

    async def retrain_models(self):
        """Retrain all models with accumulated data"""
        if len(self.training_data) < 100:
            print("⚠️ Not enough data for retraining")
            return

        print("🔄 Retraining AI models...")

        # Prepare data
        X = np.array([d['features'] for d in self.training_data])
        y = np.array([d['return'] for d in self.training_data])

        # Train ensemble models
        for name, model in self.ensemble_models.items():
            try:
                model.fit(X, y)
                print(f"✅ Retrained {name}")
            except Exception as e:
                print(f"❌ Error retraining {name}: {e}")

        # Neural network retraining would go here (more complex, requires batching)
        # For now, we rely on online learning through RL agent

        print("✅ Retraining complete")

        await self.save_models()


# ============================================================================
# GLOBAL AI ENGINE INSTANCE
# ============================================================================

ai_engine = AdvancedAIEngine()

# Public API
async def get_ai_recommendation(token_data: Dict) -> Dict:
    """Get AI recommendation for a token"""
    return await ai_engine.predict_token_performance(token_data)

async def update_ai_with_trade_result(token_data: Dict, action: str,
                                     actual_return: float, duration: int):
    """Update AI models with trade result"""
    await ai_engine.learn_from_trade(token_data, action, actual_return, duration)

async def get_ai_stats() -> Dict:
    """Get AI engine statistics"""
    return {
        'performance': ai_engine.performance_metrics,
        'training_samples': len(ai_engine.training_data),
        'rl_steps': ai_engine.trading_agent.total_steps,
        'rl_epsilon': ai_engine.trading_agent.epsilon,
        'device': str(ai_engine.device)
    }
