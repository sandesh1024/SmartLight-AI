"""
SmartLight AI - Multi-Agent DQN
Each of the 20 signals has its own DQN agent.
State:  [w_north, w_south, w_east, w_west,          # weighted lane counts (DQN learns weights)
         wait_north, wait_south, wait_east, wait_west, # how long each lane has been waiting
         neighbor_load,                                # average load of neighboring signals
         is_peak_hour,                                 # 0 or 1
         current_green]                                # which lane is currently green (0-3)
Action: 0=north, 1=south, 2=east, 3=west (which lane gets green next)
Reward: weighted_vehicles_cleared - starvation_penalty - neighbor_congestion_penalty
"""

import os
os.environ["TORCH_COMPILE_DISABLE"] = "1"
os.environ["TORCHDYNAMO_DISABLE"]   = "1"

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random
import os
from collections import deque

# ── CONFIG ──────────────────────────────────────────────────────────
STATE_SIZE    = 12   # see above
ACTION_SIZE   = 4    # 4 lanes
HIDDEN_SIZE   = 128
LR            = 0.001
GAMMA         = 0.95       # discount factor
EPSILON_START = 1.0        # start fully random
EPSILON_END   = 0.05       # minimum exploration
EPSILON_DECAY = 0.995      # decay per episode
BATCH_SIZE    = 64
MEMORY_SIZE   = 10000
TARGET_UPDATE = 10         # update target network every N episodes
MODELS_DIR    = os.path.join(os.path.dirname(__file__), "..", "models")


# ── NEURAL NETWORK ───────────────────────────────────────────────────
class DQNNetwork(nn.Module):
    """
    3-layer network.
    Input:  state vector (12 values)
    Output: Q-value for each of 4 actions
    """
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(STATE_SIZE, HIDDEN_SIZE),
            nn.ReLU(),
            nn.Linear(HIDDEN_SIZE, HIDDEN_SIZE),
            nn.ReLU(),
            nn.Linear(HIDDEN_SIZE, ACTION_SIZE)
        )

    def forward(self, x):
        return self.net(x)


# ── DQN AGENT ────────────────────────────────────────────────────────
class DQNAgent:
    """
    One DQN agent per signal (20 total).
    Learns vehicle type weights automatically through reward signal.
    """
    def __init__(self, signal_id: str):
        self.signal_id      = signal_id
        self.epsilon        = EPSILON_START
        self.memory         = deque(maxlen=MEMORY_SIZE)
        self.episode_count  = 0

        # Online network (trained every step)
        self.policy_net = DQNNetwork()
        # Target network (updated every TARGET_UPDATE episodes — stable training)
        self.target_net = DQNNetwork()
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        self.optimizer  = optim.Adam(self.policy_net.parameters(), lr=LR)
        self.loss_fn    = nn.MSELoss()

        # Vehicle type weights — DQN learns these implicitly through reward
        # Start equal, will converge to reflect true impact on traffic flow
        self.vehicle_weights = {
            'car':       1.0,
            'bus':       3.5,  # buses have higher weight due to capacity and impact on flow
            'truck':     3.0,
            'bike':      0.5,
            'rickshaw':  0.8,
            'ambulance': 10.0,   # always high priority
        }

        os.makedirs(MODELS_DIR, exist_ok=True)

    def get_weighted_count(self, type_counts: dict) -> float:
        """
        Convert raw vehicle type counts to weighted count.
        DQN learns which lanes to prioritize — indirectly learning vehicle weights.
        type_counts = {'car': 5, 'bus': 2, 'truck': 1, 'bike': 3, ...}
        """
        total = 0.0
        for vtype, count in type_counts.items():
            w = self.vehicle_weights.get(vtype, 1.0)
            total += w * count
        return total

    def build_state(self, lane_type_counts: dict, wait_times: dict,
                    neighbor_load: float, is_peak: bool, current_green: int, has_ambulance: bool = False) -> np.ndarray:
        """
        Build the 12-element state vector.
        lane_type_counts = {
            'north': {'car':5,'bus':2,...},
            'south': {'car':3,...},
            ...
        }
        wait_times = {'north': 45, 'south': 12, 'east': 30, 'west': 8}  (seconds waiting)
        """
        directions = ['north', 'south', 'east', 'west']

        # Weighted counts (normalized 0-1, max assumed 50)
        w_counts = [
            min(self.get_weighted_count(lane_type_counts.get(d, {})) / 50.0, 1.0)
            for d in directions
        ]

        # Wait times (normalized 0-1, max assumed 120s)
        w_waits = [min(wait_times.get(d, 0) / 120.0, 1.0) for d in directions]

        # Neighbor load (normalized)
        n_load = min(neighbor_load / 50.0, 1.0)

        # Peak hour flag
        peak = 1.0 if is_peak else 0.0

        # Current green (one-hot encoded as 0-1 fraction)
        cur_green = current_green / 3.0

        amb = 1.0 if has_ambulance else 0.0
        state = np.array(w_counts + w_waits + [n_load, peak, cur_green, amb], dtype=np.float32)
        return state

    def select_action(self, state: np.ndarray, force_greedy: bool = False) -> int:
        """
        Epsilon-greedy action selection.
        force_greedy=True during deployment (no exploration).
        """
        if not force_greedy and random.random() < self.epsilon:
            return random.randint(0, ACTION_SIZE - 1)

        with torch.no_grad():
            q_values = self.policy_net(torch.FloatTensor(state).unsqueeze(0))
            return q_values.argmax().item()

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def replay(self):
        """Train on a random batch from memory."""
        if len(self.memory) < BATCH_SIZE:
            return

        batch = random.sample(self.memory, BATCH_SIZE)
        states      = torch.FloatTensor(np.array([b[0] for b in batch]))
        actions     = torch.LongTensor([b[1] for b in batch])
        rewards     = torch.FloatTensor([b[2] for b in batch])
        next_states = torch.FloatTensor(np.array([b[3] for b in batch]))
        dones       = torch.FloatTensor([b[4] for b in batch])

        # Current Q values
        current_q = self.policy_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)

        # Target Q values (Bellman equation)
        with torch.no_grad():
            next_q    = self.target_net(next_states).max(1)[0]
            target_q  = rewards + GAMMA * next_q * (1 - dones)

        loss = self.loss_fn(current_q, target_q)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        return loss.item()

    def update_epsilon(self):
        self.epsilon = max(EPSILON_END, self.epsilon * EPSILON_DECAY)

    def update_target_network(self):
        self.target_net.load_state_dict(self.policy_net.state_dict())

    def end_episode(self):
        self.episode_count += 1
        self.update_epsilon()
        if self.episode_count % TARGET_UPDATE == 0:
            self.update_target_network()

    def save(self, path: str = None):
        if path is None:
            path = os.path.join(MODELS_DIR, f"dqn_{self.signal_id}.pth")
        torch.save({
            'policy_net':     self.policy_net.state_dict(),
            'target_net':     self.target_net.state_dict(),
            'epsilon':        self.epsilon,
            'episode_count':  self.episode_count,
            'vehicle_weights':self.vehicle_weights,
        }, path)
        print(f"✅ DQN saved: {self.signal_id} (episode {self.episode_count}, ε={self.epsilon:.3f})")

    def load(self, path: str = None):
        if path is None:
            path = os.path.join(MODELS_DIR, f"dqn_{self.signal_id}.pth")
        if not os.path.exists(path):
            print(f"⚠ No saved model for {self.signal_id}, starting fresh")
            return False
        checkpoint = torch.load(path, map_location='cpu')
        self.policy_net.load_state_dict(checkpoint['policy_net'])
        self.target_net.load_state_dict(checkpoint['target_net'])
        self.epsilon        = checkpoint.get('epsilon', EPSILON_END)
        self.episode_count  = checkpoint.get('episode_count', 0)
        self.vehicle_weights= checkpoint.get('vehicle_weights', self.vehicle_weights)
        print(f"✅ DQN loaded: {self.signal_id} (episode {self.episode_count}, ε={self.epsilon:.3f})")
        return True

    def calculate_reward(self, vehicles_cleared: dict, wait_times: dict,
                         type_counts: dict, emergency_handled: bool) -> float:
        """
        Reward function — DQN optimizes this.

        +points: weighted vehicles cleared this phase
        -points: starvation (any lane waiting too long)
        -points: neighbor congestion contribution
        +bonus:  emergency vehicle handled correctly
        """
        directions = ['north', 'south', 'east', 'west']

        # Base reward: weighted vehicles cleared
        reward = 0.0
        for d in directions:
            cleared = vehicles_cleared.get(d, 0)
            # Use weighted count of cleared vehicles
            wc = self.get_weighted_count(type_counts.get(d, {'car': cleared}))
            reward += wc * 0.5

        # Starvation penalty: any lane waiting > 60s
        for d in directions:
            wait = wait_times.get(d, 0)
            if wait > 60:
                reward -= (wait - 60) * 0.2   # penalty per second over 60s
            elif wait > 90:
                reward -= (wait - 90) * 0.5   # heavier penalty over 90s

        # Emergency bonus
        if emergency_handled:
            reward += 20.0

        return float(reward)


# ── SHARED AGENT POOL ────────────────────────────────────────────────
# All 20 signal agents stored here
_agent_pool: dict[str, DQNAgent] = {}

def get_agent(signal_id: str) -> DQNAgent:
    """Get or create DQN agent for a signal."""
    if signal_id not in _agent_pool:
        agent = DQNAgent(signal_id)
        agent.load()  # try to load saved weights
        _agent_pool[signal_id] = agent
    return _agent_pool[signal_id]

def save_all_agents():
    """Save all 20 agents."""
    for sid, agent in _agent_pool.items():
        agent.save()
    print(f"✅ All {len(_agent_pool)} DQN agents saved")

def get_all_agent_stats() -> dict:
    """Return stats for dashboard display."""
    return {
        sid: {
            'epsilon':       round(a.epsilon, 3),
            'episode':       a.episode_count,
            'memory_size':   len(a.memory),
            'trained':       a.episode_count > 100,
        }
        for sid, a in _agent_pool.items()
    }