# app/ai/shared_dqn.py


class SharedDQN:
    def __init__(self):
        self.lanes = ["north", "south", "east", "west"]
        self.last_selected = None
        self.same_lane_count = 0
        self.max_repeat = 2  # prevent starvation

    # -------------------------------------------------------
    # Simple smart selection
    # -------------------------------------------------------
    def select_action(self, vehicle_counts: dict):

        # Sort lanes by vehicle count descending
        sorted_lanes = sorted(
            vehicle_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        for lane, count in sorted_lanes:

            # Avoid repeating same lane too many times
            if lane == self.last_selected and self.same_lane_count >= self.max_repeat:
                continue

            # Avoid lanes with almost no vehicles
            if count <= 1:
                continue

            # Select this lane
            if lane == self.last_selected:
                self.same_lane_count += 1
            else:
                self.same_lane_count = 1

            self.last_selected = lane
            return lane

        # Fallback: choose highest anyway
        fallback_lane = sorted_lanes[0][0]
        self.last_selected = fallback_lane
        self.same_lane_count = 1
        return fallback_lane