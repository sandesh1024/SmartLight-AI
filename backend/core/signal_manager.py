"""
SmartLight AI - Signal Manager (Updated)
Manages all 20 signals with:
- YOLO vehicle counting (with type detection)
- DQN agent coordination
- Peak hour detection
- Green wave coordination
- Auto-save DQN models every 10 minutes
"""

import asyncio
import threading
import time
import random
import os
import cv2

from .signal import TrafficSignal, LANE_ORDER
from .dqn_agent  import save_all_agents, get_all_agent_stats
from .peak_detector import get_detector as get_peak_detector
from .coordination  import get_coordinator

# YOLO model
try:
    from ultralytics import YOLO
    _yolo_model = YOLO('yolov8s.pt')
    YOLO_AVAILABLE = True
    print("✅ YOLOv8s loaded")
except Exception as e:
    print(f"⚠ YOLO not available: {e}")
    YOLO_AVAILABLE = False
    _yolo_model = None

# Vehicle type mapping from YOLO class names
YOLO_CLASS_MAP = {
    'car':          'car',
    'truck':        'truck',
    'bus':          'bus',
    'motorcycle':   'bike',
    'bicycle':      'bike',
    'person':       None,           # ignore pedestrians
    'ambulance':    'ambulance',
}

VIDEOS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'videos')
)


class SignalManager:
    def __init__(self):
        self.signals: dict[str, TrafficSignal] = {}
        self._reinit_queue = set()
        self._lock         = threading.Lock()
        self._last_save    = time.time()
        self._save_interval= 600   # save DQN models every 10 min
        self._setup_signals()

    def _setup_signals(self):
        """Create all 20 signals across 5 Mumbai locations."""
        locations = {
            'bandra':     {'lat': 19.0596, 'lng': 72.8295},
            'worli':      {'lat': 19.0176, 'lng': 72.8178},
            'dadar':      {'lat': 19.0178, 'lng': 72.8478},
            'andheri':    {'lat': 19.1197, 'lng': 72.8469},
            'churchgate': {'lat': 18.9351, 'lng': 72.8253},
        }

        # Available video files
        video_files = []
        if os.path.exists(VIDEOS_DIR):
            video_files = [f for f in os.listdir(VIDEOS_DIR) if f.endswith('.mp4') and not f.endswith('.mp4.mp4')]

        for loc_name, coords in locations.items():
            for i in range(1, 5):
                signal_id = f"{loc_name}_{i}"
                name      = f"{loc_name.capitalize()} Signal {i}"

                # Assign random videos to lanes
                vm = {}

                if len(video_files) >= len(LANE_ORDER):
                    selected_videos = random.sample(video_files, len(LANE_ORDER))
                else:
                    selected_videos = [random.choice(video_files) for _ in LANE_ORDER]

                for lane, vid in zip(LANE_ORDER, selected_videos):
                    vm[lane] = vid  

                sig = TrafficSignal(
                    signal_id     = signal_id,
                    name          = name,
                    location      = loc_name,
                    lat           = coords['lat'] + random.uniform(-0.005, 0.005),
                    lng           = coords['lng'] + random.uniform(-0.005, 0.005),
                    video_mapping = vm,
                )
                self.signals[signal_id] = sig

        print(f"✅ {len(self.signals)} signals initialized")

    async def start(self):
        """Main async loop — ticks all signals every second."""
        # Start YOLO thread
        yolo_thread = threading.Thread(target=self._yolo_loop, daemon=True)
        yolo_thread.start()

        # Start peak detector thread
        peak_thread = threading.Thread(target=self._peak_loop, daemon=True)
        peak_thread.start()

        print("🔄 Signal manager running")

        while True:
            all_states    = self.get_all_states()
            coordinator   = get_coordinator()

            for sig_id, sig in self.signals.items():
                # Get neighbor load for DQN state
                neighbor_load = coordinator.get_neighbor_load(sig_id, all_states)

                # Check for green wave request
                wave = coordinator.should_prepare_green(sig_id)
                if wave and sig.state == 'RUNNING':
                    # Pre-switch to match incoming vehicle wave
                    target_lane = wave.get('lane')
                    if target_lane in LANE_ORDER:
                        print(f"🌊 [{sig.name}] Green wave from {wave['requesting_signal']} → preparing {target_lane}")

                # Tick the signal
                sig.tick(neighbor_load)

                # Notify coordinator when going green
                if sig.phase == 'GREEN' and sig.active_lane:
                    coordinator.notify_green(sig_id, sig.active_lane, sig.timer)

            # Auto-save DQN models
            if time.time() - self._last_save > self._save_interval:
                save_all_agents()
                self._last_save = time.time()

            await asyncio.sleep(1)

    def _peak_loop(self):
        """Check peak hour every 30 seconds and update all signal timings."""
        peak_detector = get_peak_detector()
        while True:
            try:
                all_states    = self.get_all_states()
                timing_config = peak_detector.update(all_states)
                # Apply to all signals
                for sig in self.signals.values():
                    sig.update_peak_timing(timing_config)
            except Exception as e:
                print(f"Peak detector error: {e}")
            time.sleep(30)

    def _yolo_loop(self):
        """Background thread — runs YOLO on lanes that need counting."""
        # Phase 1: initial count all signals
        print("🔍 Initial YOLO scan...")
        for sig in self.signals.values():
            counts = self._count_all_lanes(sig)
            sig.start_cycle(counts)
        print("✅ Initial scan complete")

        # Phase 2: ongoing per-lane detection
        while True:
            try:
                for sig in self.signals.values():
                    if not sig._cycle_ready:
                        continue
                    for lane in LANE_ORDER:
                        if sig._yolo_needed.get(lane, False):
                            count, type_counts = self._count_lane_with_types(sig, lane)
                            sig.update_lane_count(lane, count, type_counts)
                time.sleep(0.05)  # ← only change: was 0.1, now 0.05 (2x faster)
            except Exception as e:
                print(f"YOLO loop error: {e}")
                time.sleep(1)

    def _count_lane_with_types(self, sig: TrafficSignal, lane: str) -> tuple:
        video_file = sig.video_mapping.get(lane, '')
        video_path = os.path.join(VIDEOS_DIR, video_file)

        type_counts = {'car':0,'bus':0,'truck':0,'bike':0,'rickshaw':0,'ambulance':0}

        if not YOLO_AVAILABLE or not os.path.exists(video_path):
            total = random.randint(2, 20)
            type_counts['car']  = random.randint(0, total)
            type_counts['bus']  = random.randint(0, max(0, total - type_counts['car']))
            type_counts['bike'] = total - type_counts['car'] - type_counts['bus']
            return total, type_counts

        try:
            cap         = cv2.VideoCapture(video_path)
            total_frames= int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # ── FIX: random frame instead of always middle ──
            random_frame = random.randint(0, max(0, total_frames - 1))
            cap.set(cv2.CAP_PROP_POS_FRAMES, random_frame)

            ret, frame = cap.read()
            cap.release()

            if not ret:
                return 0, type_counts

            results = _yolo_model(frame, verbose=False)[0]
            count   = 0

            for box in results.boxes:
                cls_name = results.names[int(box.cls[0])].lower()
                mapped   = YOLO_CLASS_MAP.get(cls_name)
                if mapped:
                    type_counts[mapped] += 1
                    count += 1

            return count, type_counts

        except Exception as e:
            print(f"YOLO error [{sig.name}/{lane}]: {e}")
            return 0, type_counts

    def _count_all_lanes(self, sig: TrafficSignal) -> dict:
        """Count all 4 lanes for initial cycle start."""
        counts = {}
        for lane in LANE_ORDER:
            c, tc = self._count_lane_with_types(sig, lane)
            counts[lane] = c
            sig.update_lane_count(lane, c, tc)
        return counts

    def reinit_signal(self, signal_id: str):
        with self._lock:
            self._reinit_queue.add(signal_id)

    def reinit_all(self):
        with self._lock:
            self._reinit_queue.update(self.signals.keys())

    def get_all_states(self) -> dict:
        states = {}
        for sig_id, sig in self.signals.items():
            try:
                states[sig_id] = sig.get_state()
            except Exception:
                pass
        return states

    def get_system_status(self) -> dict:
        """Full system status for dashboard."""
        peak        = get_peak_detector().get_status()
        coord       = get_coordinator().get_status()
        dqn_stats   = get_all_agent_stats()
        trained     = sum(1 for s in dqn_stats.values() if s.get('trained'))

        return {
            'total_signals':     len(self.signals),
            'peak_status':       peak,
            'coordination':      coord,
            'dqn': {
                'total_agents':  len(dqn_stats),
                'trained_agents':trained,
                'agents':        dqn_stats,
            }
        }