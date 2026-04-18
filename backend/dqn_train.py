"""
SmartLight AI - DQN Training Script
Trains all 20 DQN agents using the Pygame simulation environment.
Run this BEFORE starting the backend to pre-train agents.

Usage:
    python dqn_train.py --episodes 1000 --fast

--fast: no pygame display (headless, 10x faster)
--episodes N: how many training episodes
"""

import argparse
import random
import time
import sys
import os

# ✅ Disable torch dynamo/ONNX to avoid corruption errors
os.environ["TORCH_COMPILE_DISABLE"] = "1"
os.environ["TORCHDYNAMO_DISABLE"]   = "1"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from backend.core.dqn_agent import DQNAgent, save_all_agents
LANE_ORDER = ["north", "south", "east", "west"]

# ── TRAINING ENVIRONMENT ─────────────────────────────────────────────
class TrafficEnvironment:
    """
    Lightweight traffic simulation for DQN training.
    No pygame display — just math and state.
    10x faster than visual simulation.
    """
    def __init__(self):
        self.lanes     = LANE_ORDER
        self.reset()

    def reset(self):
        """Reset to new episode."""
        self.vehicle_counts = {
            l: {'car': random.randint(0,8), 'bus': random.randint(0,3),
                'truck': random.randint(0,2), 'bike': random.randint(0,5),
                'rickshaw': random.randint(0,3), 'ambulance': 0}
            for l in self.lanes
        }
        self.wait_times   = {l: 0 for l in self.lanes}
        self.current_green= 0
        self.step_count   = 0
        self.total_cleared= 0
        self.max_steps    = 200  # steps per episode

        # Randomly spawn ambulance on any lane (10% chance)
        if random.random() < 0.1:
            amb_lane = random.choice(self.lanes)
            self.vehicle_counts[amb_lane]['ambulance'] = 1

        return self._get_state()

    def step(self, action: int):
        """
        Execute action (select which lane gets green).
        Returns: (next_state, reward, done)
        """
        self.step_count += 1
        selected_lane = self.lanes[action]

        # Simulate vehicles clearing during green phase
        green_time = self._calculate_green_time(selected_lane)
        cleared    = {}

        for lane in self.lanes:
            total = sum(self.vehicle_counts[lane].values())
            if lane == selected_lane:
                # Clear vehicles proportional to green time
                rate         = min(total, max(1, green_time // 5))
                actually_cleared = min(total, rate)
                cleared[lane] = actually_cleared

                # Reduce counts
                remaining = total - actually_cleared
                for vtype in self.vehicle_counts[lane]:
                    self.vehicle_counts[lane][vtype] = max(0,
                        int(self.vehicle_counts[lane][vtype] * (remaining / max(total,1))))

                self.wait_times[lane] = 0
                self.total_cleared   += actually_cleared
            else:
                # Other lanes accumulate new vehicles and wait time
                new_arrivals = random.randint(0, 3)
                self.vehicle_counts[lane]['car'] += new_arrivals
                self.wait_times[lane] += green_time + 3   # green + yellow

        # Calculate reward
        reward = self._calculate_reward(selected_lane, cleared)

        # Update current green
        self.current_green = action

        done = self.step_count >= self.max_steps
        return self._get_state(), reward, done

    def _calculate_green_time(self, lane: str) -> int:
        total = sum(self.vehicle_counts[lane].values())
        return max(5, min(30, total * 2))

    def _calculate_reward(self, selected_lane: str, cleared: dict) -> float:
        reward = 0.0

        # Reward: vehicles cleared (weighted by type)
        lc     = self.vehicle_counts[selected_lane]
        # Bus and truck clear slowly but represent more people
        reward += cleared.get(selected_lane, 0) * 1.0
        reward += lc.get('bus', 0) * 0.5      # bonus for clearing buses
        reward += lc.get('ambulance', 0) * 5.0 # big bonus for ambulance

        # Penalty: starvation (lanes waiting too long)
        for lane in self.lanes:
            wt = self.wait_times.get(lane, 0)
            if wt > 60:  reward -= (wt - 60)  * 0.1
            if wt > 120: reward -= (wt - 120) * 0.3

        # Penalty: total vehicles still waiting
        total_waiting = sum(sum(lc.values()) for lc in self.vehicle_counts.values())
        reward -= total_waiting * 0.05

        return float(reward)

    def _get_state(self) -> np.ndarray:
        directions = self.lanes
        # Weighted counts (normalized)
        w_counts = [min(sum(self.vehicle_counts[d].values()) / 30.0, 1.0) for d in directions]
        # Wait times (normalized)
        w_waits  = [min(self.wait_times.get(d, 0) / 120.0, 1.0) for d in directions]
        # Neighbor load (simplified: average of all lanes)
        avg_load = np.mean(w_counts)
        # Peak hour: 50% chance during training (to learn both scenarios)
        is_peak  = random.random() < 0.5
        # Current green
        cur_green = self.current_green / 3.0

        has_ambulance = 1.0 if any(
            self.vehicle_counts[d].get('ambulance', 0) > 0
            for d in self.lanes
        ) else 0.0
        return np.array(w_counts + w_waits + [avg_load, float(is_peak), cur_green, has_ambulance], dtype=np.float32)

# ── TRAINING LOOP ────────────────────────────────────────────────────
def train(n_episodes: int = 1000, signal_id: str = 'train_agent', verbose: bool = True):
    """Train a single DQN agent."""
    env   = TrafficEnvironment()
    agent = DQNAgent(signal_id)

    best_reward  = float('-inf')
    reward_history = []

    print(f"\n🚦 Training DQN for {signal_id}")
    print(f"   Episodes: {n_episodes} | State: 12 | Actions: 4")
    print(f"   Saving to: backend/models/dqn_{signal_id}.pth\n")

    for ep in range(1, n_episodes + 1):
        state      = env.reset()
        total_rew  = 0.0
        steps      = 0

        while True:
            # Select action
            action         = agent.select_action(state)
            next_state, reward, done = env.step(action)

            # Remember and train
            agent.remember(state, action, reward, next_state, done)
            agent.replay()

            state      = next_state
            total_rew += reward
            steps     += 1

            if done:
                break

        agent.end_episode()
        reward_history.append(total_rew)

        if total_rew > best_reward:
            best_reward = total_rew
            agent.save()   # save best model

        if verbose and ep % 50 == 0:
            avg_50 = np.mean(reward_history[-50:])
            print(f"  Ep {ep:4d}/{n_episodes} | "
                  f"Reward: {total_rew:8.1f} | "
                  f"Avg50: {avg_50:8.1f} | "
                  f"ε: {agent.epsilon:.3f} | "
                  f"Best: {best_reward:.1f} | "
                  f"Cleared: {env.total_cleared}")

    print(f"\n✅ Training complete! Best reward: {best_reward:.1f}")
    return agent


def train_all_signals(n_episodes: int = 1000):
    """
    Train all 20 signal agents.
    Since they all face similar environments, we train one master agent
    then copy weights to all 20 (transfer learning).
    Fine-tuning per signal happens in production.
    """
    print("="*60)
    print("SmartLight AI — Multi-Agent DQN Training")
    print("="*60)
    print(f"Training master agent for {n_episodes} episodes...")
    print("This will be transferred to all 20 signal agents.\n")

    # Train master agent
    master_agent = train(n_episodes, 'master', verbose=True)

    # Transfer weights to all 20 signal agents
    signal_ids = []
    locations  = ['bandra','worli','dadar','andheri','churchgate']
    for loc in locations:
        for i in range(1, 5):
            signal_ids.append(f"{loc}_{i}")

    print(f"\n📋 Transferring weights to {len(signal_ids)} signal agents...")
    for sid in signal_ids:
        agent = DQNAgent(sid)
        # Copy master weights
        agent.policy_net.load_state_dict(master_agent.policy_net.state_dict())
        agent.target_net.load_state_dict(master_agent.target_net.state_dict())
        agent.epsilon       = 0.1    # some exploration for fine-tuning
        agent.episode_count = n_episodes
        agent.save()
        print(f"  ✅ {sid}")

    print(f"\n🎉 All {len(signal_ids)} agents trained and saved!")
    print(f"   Models saved in: backend/models/")
    print(f"   Start the backend now — DQN will be used automatically.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train SmartLight DQN agents")
    parser.add_argument('--episodes', type=int, default=1000,
                        help='Number of training episodes (default: 1000)')
    parser.add_argument('--signal',   type=str, default=None,
                        help='Train specific signal only (default: train all)')
    args = parser.parse_args()

    if args.signal:
        train(args.episodes, args.signal)
    else:
        train_all_signals(args.episodes)