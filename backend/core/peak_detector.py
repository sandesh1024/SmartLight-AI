"""
SmartLight AI - Peak Hour Detector
Monitors vehicle counts over time, detects rush hours,
adjusts MIN/MAX green times automatically.
"""

from datetime import datetime
from collections import deque
import statistics

# Peak hour config
PEAK_HOURS = {
    'morning': (7, 10),    # 7AM - 10AM
    'evening': (17, 21),   # 5PM - 9PM
}

# Green time adjustments during peak
NORMAL_MIN_GREEN = 5
NORMAL_MAX_GREEN = 30
PEAK_MIN_GREEN   = 8    # more minimum time during peak
PEAK_MAX_GREEN   = 45   # allow longer green during peak

# Pattern detection (independent of clock time)
PATTERN_WINDOW   = 10   # look at last 10 cycles
HIGH_LOAD_THRESH = 0.7  # 70% of signals at HIGH = peak detected


class PeakHourDetector:
    """
    Two methods of peak detection:
    1. Clock-based: standard Mumbai rush hours
    2. Pattern-based: detect actual high load regardless of time
    """

    def __init__(self):
        self.load_history    = deque(maxlen=PATTERN_WINDOW)
        self.is_peak         = False
        self.peak_type       = None    # 'morning' | 'evening' | 'pattern' | None
        self.peak_start_time = None
        self.peak_duration   = 0       # minutes in peak
        self.total_vehicles_peak = 0
        self.adjustment_log  = []

    def update(self, all_signal_states: dict) -> dict:
        """
        Call every cycle with all 20 signal states.
        Returns adjustment config for signal timing.
        """
        now        = datetime.now()
        hour       = now.hour

        # Method 1: Clock-based peak detection
        clock_peak = False
        peak_type  = None
        for ptype, (start, end) in PEAK_HOURS.items():
            if start <= hour < end:
                clock_peak = True
                peak_type  = ptype
                break

        # Method 2: Pattern-based — count how many signals are HIGH load
        total_signals = len(all_signal_states)
        if total_signals > 0:
            high_count = sum(
                1 for sig in all_signal_states.values()
                if self._get_total_vehicles(sig) >= 30
            )
            load_ratio = high_count / total_signals
            self.load_history.append(load_ratio)

            # If last N cycles averaged > threshold = pattern peak
            if len(self.load_history) >= 5:
                avg_load   = statistics.mean(self.load_history)
                pattern_peak = avg_load >= HIGH_LOAD_THRESH
            else:
                pattern_peak = False
        else:
            pattern_peak = False
            load_ratio   = 0

        # Combine both methods
        was_peak   = self.is_peak
        self.is_peak = clock_peak or pattern_peak

        if self.is_peak:
            self.peak_type = peak_type or ('pattern' if pattern_peak else None)
            if not was_peak:
                self.peak_start_time = now
                print(f"🔴 PEAK HOUR DETECTED: {self.peak_type} at {now.strftime('%H:%M')}")
            self.peak_duration = int((now - self.peak_start_time).total_seconds() / 60) if self.peak_start_time else 0
        else:
            if was_peak:
                print(f"🟢 Peak hour ended after {self.peak_duration} minutes")
            self.peak_type       = None
            self.peak_start_time = None
            self.peak_duration   = 0

        return self.get_timing_config()

    def get_timing_config(self) -> dict:
        """Return timing adjustments based on current peak status."""
        if self.is_peak:
            return {
                'is_peak':   True,
                'peak_type': self.peak_type,
                'min_green': PEAK_MIN_GREEN,
                'max_green': PEAK_MAX_GREEN,
                'cycle_total': 80,          # longer total cycle during peak
                'yellow_time': 3,
                'message':   f"Peak Hour Active ({self.peak_type}) — Extended green times",
            }
        else:
            return {
                'is_peak':    False,
                'peak_type':  None,
                'min_green':  NORMAL_MIN_GREEN,
                'max_green':  NORMAL_MAX_GREEN,
                'cycle_total': 60,
                'yellow_time': 3,
                'message':    "Normal traffic conditions",
            }

    def get_status(self) -> dict:
        """Full status for dashboard display."""
        now  = datetime.now()
        hour = now.hour

        # Find next peak
        next_peak = None
        for ptype, (start, end) in PEAK_HOURS.items():
            if hour < start:
                next_peak = f"{ptype.capitalize()} peak at {start}:00"
                break
        if not next_peak:
            next_peak = "Morning peak at 07:00 (tomorrow)"

        return {
            'is_peak':          self.is_peak,
            'peak_type':        self.peak_type,
            'peak_duration_min':self.peak_duration,
            'current_time':     now.strftime('%H:%M'),
            'next_peak':        next_peak,
            'load_history':     list(self.load_history),
            'avg_load':         round(statistics.mean(self.load_history), 2) if self.load_history else 0,
            'min_green':        PEAK_MIN_GREEN if self.is_peak else NORMAL_MIN_GREEN,
            'max_green':        PEAK_MAX_GREEN if self.is_peak else NORMAL_MAX_GREEN,
            'timing_config':    self.get_timing_config(),
        }

    def _get_total_vehicles(self, sig: dict) -> int:
        counts = sig.get('vehicle_counts', {})
        return sum(counts.values()) if counts else 0


# Singleton instance
_detector = PeakHourDetector()

def get_detector() -> PeakHourDetector:
    return _detector