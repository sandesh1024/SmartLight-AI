# backend/core/signal_manager.py

import asyncio
import random
import threading
import time
from typing import Dict

from backend.core.signal import Signal
from backend.ai.video_manager import VideoManager
from backend.ai.yolo_engine import YOLOEngine
from backend.ai.shared_dqn import SharedDQN


class SignalManager:
    def __init__(self):
        self.signals: Dict[str, Signal] = {}
        self.running       = False
        self._reinit_queue = []

        video_paths = {
            "lane1": "videos/video1.mp4",
            "lane2": "videos/video2.mp4",
            "lane3": "videos/video3.mp4",
            "lane4": "videos/video4.mp4",
            "lane5": "videos/video5.mp4",
            "lane6": "videos/video6.mp4",
            "lane7": "videos/video7.mp4",
            "lane8": "videos/video8.mp4",
        }

        self.video_manager = VideoManager(video_paths)
        self.yolo_engine   = YOLOEngine(model_path="yolov8s.pt")
        self.dqn           = SharedDQN()

        self._initialize_signals()
        threading.Thread(target=self._yolo_loop, daemon=True).start()

    def _initialize_signals(self):
        locations = ["bandra", "worli", "dadar", "andheri", "churchgate"]
        video_ids = list(self.video_manager.video_paths.keys())

        for location in locations:
            for i in range(4):
                signal_id = f"{location}_{i+1}"
                shuffled  = video_ids.copy()
                random.shuffle(shuffled)
                mapping = {
                    "north": shuffled[0],
                    "south": shuffled[1],
                    "east":  shuffled[2],
                    "west":  shuffled[3],
                }
                self.signals[signal_id] = Signal(
                    signal_id=signal_id,
                    name=f"{location.title()} Signal {i+1}",
                    location=location,
                    video_mapping=mapping,
                )

    def _count_lane(self, signal: Signal, lane: str) -> int:
        video_id = signal.video_mapping.get(lane)
        if not video_id:
            return 0
        frame = self.video_manager.get_frame(video_id)
        if frame is None:
            return 0
        count = self.yolo_engine.count_vehicles(frame)
        return count

    def _count_all_lanes(self, signal: Signal) -> dict:
        return {lane: self._count_lane(signal, lane) for lane in signal.lane_order}

    def reinit_signal(self, signal_id: str):
        if signal_id not in self._reinit_queue:
            self._reinit_queue.append(signal_id)

    def reinit_all(self):
        self._reinit_queue = list(self.signals.keys())

    def _yolo_loop(self):
        print("🔍 YOLO: Initial count starting...")

        # Phase 1 — init all signals
        for signal_id, signal in self.signals.items():
            try:
                counts = self._count_all_lanes(signal)
                signal.start_cycle(counts)
            except Exception as e:
                print(f"❌ Init error {signal_id}: {e}")
                signal.start_cycle({"north": 0, "south": 0, "east": 0, "west": 0})
            time.sleep(0.3)

        print("🟢 YOLO: All signals initialized. Watching per-lane requests...")

        # Phase 2 — monitor _yolo_needed flags per lane
        while True:
            try:
                # Reinit queue (from reset/optimize commands)
                if self._reinit_queue:
                    sid    = self._reinit_queue.pop(0)
                    signal = self.signals.get(sid)
                    if signal:
                        counts = self._count_all_lanes(signal)
                        signal.start_cycle(counts)
                    continue

                # Scan all signals for any lane needing a fresh YOLO count
                for signal in self.signals.values():
                    if not signal._cycle_ready or signal._override_active:
                        continue

                    for lane in signal.lane_order:
                        if signal._yolo_needed.get(lane, False):
                            # Run YOLO on just this one lane
                            count = self._count_lane(signal, lane)
                            # ✅ This directly mutates signal.vehicle_counts[lane]
                            # which is the SAME dict returned by get_state()
                            signal.update_lane_count(lane, count)

            except Exception as e:
                print(f"YOLO loop error: {e}")

            time.sleep(0.1)  # fast scan — catches requests quickly

    async def start(self):
        self.running = True
        while self.running:
            for signal in self.signals.values():
                signal.tick()
            await asyncio.sleep(1)

    def get_all_states(self):
        return {
            sid: signal.get_state()
            for sid, signal in self.signals.items()
        }