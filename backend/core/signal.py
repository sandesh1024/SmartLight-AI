"""
SmartLight AI - Signal (Updated)
Integrates:
- DQN agent per signal (decides which lane goes green next)
- Peak hour timing adjustments
- Vehicle type weighted counts
- Coordination with neighbors
"""

import time
import threading
from typing import Optional

# Lane order and direction mapping
LANE_ORDER   = ['north', 'south', 'east', 'west']
DIR_TO_IDX   = {d: i for i, d in enumerate(LANE_ORDER)}

# Default timing
DEFAULT_YELLOW   = 3
DEFAULT_MIN_GREEN= 5
DEFAULT_MAX_GREEN= 30
CYCLE_TOTAL      = 60   # total green seconds per full cycle (normal)


class TrafficSignal:
    """
    One signal = one intersection with 4 lanes (N/S/E/W).
    Has its own DQN agent that decides which lane gets green next.
    """

    def __init__(self, signal_id: str, name: str, location: str,
                 lat: float, lng: float, video_mapping: dict):
        self.signal_id    = signal_id
        self.name         = name
        self.location     = location
        self.lat          = lat
        self.lng          = lng
        self.video_mapping= video_mapping   # {'north':'lane1',...}

        # ── Current state ──────────────────────────────────────────
        self.state        = 'WAITING'       # WAITING | RUNNING | OVERRIDE | EMERGENCY
        self.active_lane  = None            # which lane is currently green
        self.phase        = 'RED'           # RED | GREEN | YELLOW
        self.timer        = 0
        self.phase_start  = time.time()

        # ── Vehicle data ───────────────────────────────────────────
        self.vehicle_counts     = {'north':0, 'south':0, 'east':0, 'west':0}
        self.vehicle_type_counts= {          # detailed breakdown per lane
            'north': {'car':0,'bus':0,'truck':0,'bike':0,'rickshaw':0,'ambulance':0},
            'south': {'car':0,'bus':0,'truck':0,'bike':0,'rickshaw':0,'ambulance':0},
            'east':  {'car':0,'bus':0,'truck':0,'bike':0,'rickshaw':0,'ambulance':0},
            'west':  {'car':0,'bus':0,'truck':0,'bike':0,'rickshaw':0,'ambulance':0},
        }
        self.wait_times         = {'north':0,'south':0,'east':0,'west':0}
        self.vehicles_cleared   = {'north':0,'south':0,'east':0,'west':0}

        # ── Timing ────────────────────────────────────────────────
        self.lane_timings       = {}
        self.min_green          = DEFAULT_MIN_GREEN
        self.max_green          = DEFAULT_MAX_GREEN
        self.cycle_total        = CYCLE_TOTAL
        self.yellow_duration    = DEFAULT_YELLOW

        # ── DQN ───────────────────────────────────────────────────
        self._dqn_ready         = False
        self._dqn_agent         = None       # loaded lazily
        self._dqn_last_state    = None
        self._dqn_last_action   = None
        self._use_dqn           = False      # False until agent is trained enough

        # ── Emergency / Override ───────────────────────────────────
        self.emergency          = False
        self._override_lane     = None
        self._override_color    = None
        self._override_timer    = 0

        # ── Coordination ──────────────────────────────────────────
        self._yolo_needed       = {l: False for l in LANE_ORDER}
        self._cycle_ready       = False

        # ── Peak hour ─────────────────────────────────────────────
        self.is_peak            = False
        self.peak_type          = None

        self._lock              = threading.Lock()
        
        self._last_yolo_scan       = time.time()
        self._yolo_rescan_interval = 5

    # ── DQN INTEGRATION ──────────────────────────────────────────────
    def get_dqn_agent(self):
        """Lazily load DQN agent for this signal."""
        if self._dqn_agent is None:
            from .dqn_agent import get_agent
            self._dqn_agent = get_agent(self.signal_id)
            self._dqn_ready = True
        return self._dqn_agent

    def select_next_lane_dqn(self, neighbor_load: float) -> str:
        """
        Use DQN to select which lane gets green next.
        Falls back to proportional if DQN not trained enough.
        """
        agent = self.get_dqn_agent()

        # Build state for DQN
        state = agent.build_state(
            lane_type_counts=self.vehicle_type_counts,
            wait_times=self.wait_times,
            neighbor_load=neighbor_load,
            is_peak=self.is_peak,
            current_green=DIR_TO_IDX.get(self.active_lane, 0),
            has_ambulance=any(
                self.vehicle_type_counts.get(l, {}).get('ambulance', 0) > 0
                    for l in LANE_ORDER
            ),
        )

        # Use DQN if trained enough (>100 episodes), else greedy
        if agent.episode_count > 100:
            action = agent.select_action(state, force_greedy=True)
            self._use_dqn = True
        else:
            # Fallback: pick lane with highest weighted count
            action = self._greedy_lane_selection()
            self._use_dqn = False

        self._dqn_last_state  = state
        self._dqn_last_action = action

        return LANE_ORDER[action]

    def _greedy_lane_selection(self) -> int:
        """Pick lane with most vehicles (fallback when DQN not trained)."""
        counts = [self.vehicle_counts.get(l, 0) for l in LANE_ORDER]
        return counts.index(max(counts))

    def record_dqn_reward(self, neighbor_load: float):
        """Called after a green phase ends — give reward to DQN agent."""
        if self._dqn_last_state is None or self._dqn_last_action is None:
            return

        agent   = self.get_dqn_agent()

        # Calculate reward
        reward  = agent.calculate_reward(
            vehicles_cleared  = self.vehicles_cleared,
            wait_times        = self.wait_times,
            type_counts       = self.vehicle_type_counts,
            emergency_handled = self.emergency,
        )

        # Build new state
        new_state = agent.build_state(
            lane_type_counts  = self.vehicle_type_counts,
            wait_times        = self.wait_times,
            neighbor_load     = neighbor_load,
            is_peak           = self.is_peak,
            current_green     = DIR_TO_IDX.get(self.active_lane, 0),
        )

        # Store in replay memory
        agent.remember(self._dqn_last_state, self._dqn_last_action,
                       reward, new_state, False)

        # Train
        agent.replay()

        # Reset cleared vehicles for next phase
        self.vehicles_cleared = {'north':0,'south':0,'east':0,'west':0}

    # ── VEHICLE COUNTS ────────────────────────────────────────────────
    def update_lane_count(self, lane: str, count: int,
                          type_counts: dict = None):
        """Update vehicle count for a lane. type_counts = {'car':3,'bus':1,...}"""
        self.vehicle_counts[lane] = count
        if type_counts:
            self.vehicle_type_counts[lane] = type_counts
        # Queue YOLO for next lane
        self._yolo_needed[lane] = False

    def get_weighted_count(self, lane: str) -> float:
        """Get DQN-weighted vehicle count for a lane."""
        agent = self.get_dqn_agent()
        return agent.get_weighted_count(self.vehicle_type_counts.get(lane, {}))

    # ── TIMING ────────────────────────────────────────────────────────
    def update_peak_timing(self, timing_config: dict):
        """Update timing parameters from peak detector."""
        self.min_green   = timing_config.get('min_green',   DEFAULT_MIN_GREEN)
        self.max_green   = timing_config.get('max_green',   DEFAULT_MAX_GREEN)
        self.cycle_total = timing_config.get('cycle_total', CYCLE_TOTAL)
        self.is_peak     = timing_config.get('is_peak',     False)
        self.peak_type   = timing_config.get('peak_type',   None)

    def calculate_timings(self) -> dict:
        """
        Proportional green time allocation using weighted counts.
        DQN decides ORDER, this decides DURATION.
        """
        weighted = {l: max(self.get_weighted_count(l), 0.1) for l in LANE_ORDER}
        total_w  = sum(weighted.values())
        timings  = {}

        for lane in LANE_ORDER:
            raw_time = (weighted[lane] / total_w) * self.cycle_total
            clamped  = max(self.min_green, min(self.max_green, raw_time))
            timings[lane] = round(clamped)

        # Normalize to cycle total
        diff = self.cycle_total - sum(timings.values())
        if diff != 0:
            timings[LANE_ORDER[0]] += diff

        self.lane_timings = timings
        return timings

    # ── SIGNAL TICK ───────────────────────────────────────────────────
    def tick(self, neighbor_load: float = 0.0):
        """Called every 1 second by signal_manager."""
        with self._lock:
            if self.state == 'WAITING':
                return

            # Update wait times for non-green lanes
            for lane in LANE_ORDER:
                if lane != self.active_lane:
                    self.wait_times[lane] = self.wait_times.get(lane, 0) + 1
                else:
                    self.wait_times[lane] = 0

            # Handle override
            if self.state == 'OVERRIDE':
                self._tick_override()
                return

            # Handle emergency
            if self.emergency and self.state != 'EMERGENCY':
                self._start_emergency()
                return

            self._tick_normal(neighbor_load)

    def _tick_normal(self, neighbor_load: float):
        self.timer = max(0, self.timer - 1)

        # ── FIX: rescan every 5s during BOTH green and yellow ──
        now = time.time()
        if self.phase in ('GREEN', 'YELLOW'):
            if now - self._last_yolo_scan >= self._yolo_rescan_interval:
                self._yolo_needed = {l: True for l in LANE_ORDER}
                self._last_yolo_scan = now

        if self.phase == 'GREEN' and self.timer <= 0:
            self.record_dqn_reward(neighbor_load)
            self._start_yellow()

        elif self.phase == 'YELLOW' and self.timer <= 0:
            self._start_next_lane_dqn(neighbor_load) 

    def _start_next_lane_dqn(self, neighbor_load: float):
        """Start green for next lane — DQN decides which one."""
    
        # DQN picks next lane FIRST (using current counts)
        next_lane = self.select_next_lane_dqn(neighbor_load)

        # Queue YOLO only for next lane now (not all 4 at once)
        self._yolo_needed = {l: False for l in LANE_ORDER}
        self._yolo_needed[next_lane] = True

        # Recalculate timings with updated counts
        self.calculate_timings()
        green_time = self.lane_timings.get(next_lane, self.min_green)

        self.active_lane = next_lane
        self.phase       = 'GREEN'
        self.timer       = green_time
        self.phase_start = time.time()

        print(f"[{self.name}] {'DQN' if self._use_dqn else 'Greedy'}→ {next_lane} GREEN {green_time}s "
            f"| counts: {self.vehicle_counts} | peak: {self.is_peak}")

    def _start_yellow(self):
        self.phase = 'YELLOW'
        self.timer = self.yellow_duration

        # ── FIX: scan ALL 4 lanes during yellow (including current lane) ──
        self._yolo_needed = {l: True for l in LANE_ORDER}  # was skipping active lane
        self._last_yolo_scan = time.time()

    def _start_emergency(self):
        """Emergency: find ambulance lane, give it immediate green."""
        emergency_lane = None
        for lane, tc in self.vehicle_type_counts.items():
            if tc.get('ambulance', 0) > 0:
                emergency_lane = lane
                break

        if not emergency_lane:
            self.emergency = False
            return

        self.state       = 'EMERGENCY'
        self.active_lane = emergency_lane
        self.phase       = 'GREEN'
        self.timer       = 20   # 20s emergency green
        print(f"🚨 [{self.name}] EMERGENCY GREEN → {emergency_lane}")

    def _tick_override(self):
        self._override_timer -= 1
        if self._override_timer <= 0:
            self.state           = 'RUNNING'
            self._override_lane  = None
            self._override_color = None

    def start_cycle(self, counts: dict):
        """Initialize and start the signal cycle."""
        for lane, count in counts.items():
            self.vehicle_counts[lane] = count

        self.calculate_timings()
        first_lane = LANE_ORDER[0]
        self.active_lane   = first_lane
        self.phase         = 'GREEN'
        self.timer         = self.lane_timings.get(first_lane, self.min_green)
        self.state         = 'RUNNING'
        self._cycle_ready  = True
        print(f"[{self.name}] Cycle started → {first_lane} {self.timer}s")

    def manual_override(self, lane: str, color: str = 'green', duration: int = 15):
        with self._lock:
            self.state           = 'OVERRIDE'
            self.active_lane     = lane
            self.phase           = color.upper()
            self.timer           = duration
            self._override_lane  = lane
            self._override_color = color
            self._override_timer = duration

    def reset(self):
        with self._lock:
            self.state        = 'WAITING'
            self.active_lane  = None
            self.phase        = 'RED'
            self.timer        = 0
            self.emergency    = False
            self._cycle_ready = False
            self._yolo_needed = {l: False for l in LANE_ORDER}
            self.wait_times   = {'north':0,'south':0,'east':0,'west':0}

    def get_state(self) -> dict:
        agent      = self.get_dqn_agent() if self._dqn_ready else None
        return {
            'id':               self.signal_id,
            'name':             self.name,
            'location':         self.location,
            'lat':              self.lat,
            'lng':              self.lng,
            'state':            self.state,
            'active_lane':      self.active_lane,
            'phase':            self.phase,
            'timer':            self.timer,
            'vehicle_counts':   self.vehicle_counts,
            'vehicle_type_counts': self.vehicle_type_counts,
            'lane_timings':     self.lane_timings,
            'wait_times':       self.wait_times,
            'emergency':        self.emergency,
            'is_peak':          self.is_peak,
            'peak_type':        self.peak_type,
            'video_mapping':    self.video_mapping,
            'dqn': {
                'using_dqn':    self._use_dqn,
                'episodes':     agent.episode_count if agent else 0,
                'epsilon':      round(agent.epsilon, 3) if agent else 1.0,
                'trained':      (agent.episode_count > 100) if agent else False,
            }
        }