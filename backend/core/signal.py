# backend/core/signal.py

class Signal:
    def __init__(self, signal_id: str, name: str, location: str, video_mapping: dict):
        self.id            = signal_id
        self.name          = name
        self.location      = location
        self.video_mapping = video_mapping

        self.active_lane    = None
        self.phase          = "WAITING"
        self.timer          = 0
        # ✅ This is what gets sent to frontend — must always stay updated
        self.vehicle_counts = {"north": 0, "south": 0, "east": 0, "west": 0}
        self.emergency      = False

        self.CYCLE_TOTAL     = 60
        self.MIN_GREEN       = 5
        self.MAX_GREEN       = 30
        self.YELLOW_DURATION = 3

        self.lane_order    = ["north", "south", "east", "west"]
        self.lane_timings  = {}
        self.current_index = 0
        self._tick_counter = 0
        self._cycle_ready  = False

        # Which lane needs YOLO next
        self._yolo_needed  = {lane: False for lane in ["north", "south", "east", "west"]}

        self._override_active = False
        self._override_ticks  = 0

    def calculate_timings(self, counts: dict) -> dict:
        total = sum(counts.values())
        if total == 0:
            equal = self.CYCLE_TOTAL // 4
            return {lane: equal for lane in self.lane_order}

        timings = {}
        for lane in self.lane_order:
            proportion = counts.get(lane, 0) / total
            raw        = proportion * self.CYCLE_TOTAL
            timings[lane] = max(self.MIN_GREEN, min(self.MAX_GREEN, int(raw)))

        diff = self.CYCLE_TOTAL - sum(timings.values())
        if diff != 0:
            busiest = max(timings, key=timings.get)
            timings[busiest] = max(self.MIN_GREEN, min(self.MAX_GREEN, timings[busiest] + diff))

        return timings

    def start_cycle(self, counts: dict):
        # ✅ Directly assign — no dict() wrapper that could lose reference
        self.vehicle_counts["north"] = counts.get("north", 0)
        self.vehicle_counts["south"] = counts.get("south", 0)
        self.vehicle_counts["east"]  = counts.get("east",  0)
        self.vehicle_counts["west"]  = counts.get("west",  0)

        self.lane_timings  = self.calculate_timings(self.vehicle_counts)
        self.current_index = 0
        self._cycle_ready  = True

        # Request YOLO for first lane immediately (so counts refresh right away)
        self._yolo_needed = {lane: True for lane in self.lane_order}

        self._start_next_lane()
        print(f"[{self.name}] Cycle started: counts={self.vehicle_counts} timings={self.lane_timings}")

    def _start_next_lane(self):
        lane               = self.lane_order[self.current_index]
        self.active_lane   = lane
        self.phase         = "GREEN"
        self._tick_counter = self.lane_timings.get(lane, self.MIN_GREEN)
        self.timer         = self._tick_counter

        # Request YOLO for the NEXT lane so it's ready before that lane starts
        next_index = (self.current_index + 1) % len(self.lane_order)
        next_lane  = self.lane_order[next_index]
        self._yolo_needed[next_lane] = True

    def tick(self):
        if not self._cycle_ready:
            return

        if self._override_active:
            self._override_ticks -= 1
            self.timer = max(self._override_ticks, 0)
            if self._override_ticks <= 0:
                self._override_active = False
                self.emergency        = False
                self._start_next_lane()
            return

        self._tick_counter -= 1
        self.timer = max(self._tick_counter, 0)

        if self.phase == "GREEN":
            if self._tick_counter <= 0:
                self.phase         = "YELLOW"
                self._tick_counter = self.YELLOW_DURATION
                self.timer         = self._tick_counter

        elif self.phase == "YELLOW":
            if self._tick_counter <= 0:
                # Move to next lane
                self.current_index = (self.current_index + 1) % len(self.lane_order)

                # Recalculate timings with whatever counts we have now
                # (YOLO thread keeps updating vehicle_counts in real time)
                self.lane_timings = self.calculate_timings(self.vehicle_counts)

                self._start_next_lane()

    def update_lane_count(self, lane: str, count: int):
        """
        Called by YOLO thread when a fresh count is ready for a lane.
        Directly mutates vehicle_counts — same dict object that get_state() returns.
        No copying, no wrapping — guaranteed to show in WebSocket immediately.
        """
        self.vehicle_counts[lane] = count
        self._yolo_needed[lane]   = False
        print(f"[{self.name}] YOLO updated {lane}: {count} vehicles → counts now {self.vehicle_counts}")

    def manual_override(self, lane: str, color: str, duration: int = 15):
        self._override_active = True
        self._override_ticks  = duration
        self.timer            = duration
        if color == "green":
            self.active_lane = lane
            self.phase       = "GREEN"
        elif color == "yellow":
            self.phase = "YELLOW"
        elif color == "red":
            self.active_lane = None
            self.phase       = "RED"

    def reset(self):
        self._override_active = False
        self._override_ticks  = 0
        self._cycle_ready     = False
        self._yolo_needed     = {lane: False for lane in self.lane_order}
        self.active_lane      = None
        self.phase            = "WAITING"
        self.timer            = 0
        self.emergency        = False

    # Legacy compatibility
    def update_vehicle_counts(self, counts: dict):
        for lane, count in counts.items():
            if lane in self.vehicle_counts:
                self.vehicle_counts[lane] = count

    def set_next_lane(self, lane: str):
        pass

    def set_next_cycle(self, counts: dict):
        for lane, count in counts.items():
            self.update_lane_count(lane, count)

    def set_lane_count(self, lane: str, count: int):
        self.update_lane_count(lane, count)

    def get_state(self) -> dict:
        return {
            "id":             self.id,
            "name":           self.name,
            "location":       self.location,
            "active_lane":    self.active_lane,
            "phase":          self.phase,
            "timer":          self.timer,
            # ✅ Return the actual dict — not a copy — so mutations show instantly
            "vehicle_counts": self.vehicle_counts,
            "lane_timings":   self.lane_timings,
            "emergency":      self.emergency,
            "video_mapping":  self.video_mapping,
            "cycle_ready":    self._cycle_ready,
        }