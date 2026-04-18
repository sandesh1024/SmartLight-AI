"""
SmartLight AI - Multi-Intersection Coordination
Implements green wave: when a signal goes green,
neighboring signals prepare so vehicles don't stop twice.

Each signal knows its neighbors (defined by road connectivity).
When signal A goes green, it notifies neighbors B and C.
Neighbors pre-calculate their next green timing to create a wave.
"""

from typing import Dict, List, Optional
import time

# Road network — which signals are neighbors on the same road
# Format: signal_id → list of neighbor signal_ids in order of traffic flow
SIGNAL_NEIGHBORS = {
    # Bandra corridor
    'bandra_1': ['bandra_2', 'worli_1'],
    'bandra_2': ['bandra_1', 'bandra_3'],
    'bandra_3': ['bandra_2', 'bandra_4'],
    'bandra_4': ['bandra_3', 'dadar_1'],

    # Worli corridor
    'worli_1':  ['bandra_1', 'worli_2'],
    'worli_2':  ['worli_1',  'worli_3'],
    'worli_3':  ['worli_2',  'worli_4'],
    'worli_4':  ['worli_3',  'dadar_2'],

    # Dadar corridor
    'dadar_1':  ['bandra_4', 'dadar_2'],
    'dadar_2':  ['worli_4',  'dadar_3'],
    'dadar_3':  ['dadar_2',  'dadar_4'],
    'dadar_4':  ['dadar_3',  'andheri_1'],

    # Andheri corridor
    'andheri_1':['dadar_4',  'andheri_2'],
    'andheri_2':['andheri_1','andheri_3'],
    'andheri_3':['andheri_2','andheri_4'],
    'andheri_4':['andheri_3','churchgate_1'],

    # Churchgate corridor
    'churchgate_1':['andheri_4', 'churchgate_2'],
    'churchgate_2':['churchgate_1','churchgate_3'],
    'churchgate_3':['churchgate_2','churchgate_4'],
    'churchgate_4':['churchgate_3','churchgate_1'],
}

# Average vehicle travel time between neighboring signals (seconds)
# Used to time the green wave offset
TRAVEL_TIMES = {
    ('bandra_1','bandra_2'): 25,
    ('bandra_2','bandra_3'): 20,
    ('bandra_3','bandra_4'): 22,
    ('bandra_4','dadar_1'):  35,
    ('worli_1','worli_2'):   18,
    ('worli_2','worli_3'):   20,
    ('worli_3','worli_4'):   22,
    ('worli_4','dadar_2'):   30,
    ('dadar_1','dadar_2'):   25,
    ('dadar_2','dadar_3'):   20,
    ('dadar_3','dadar_4'):   22,
    ('dadar_4','andheri_1'): 40,
    ('andheri_1','andheri_2'):20,
    ('andheri_2','andheri_3'):22,
    ('andheri_3','andheri_4'):25,
    ('andheri_4','churchgate_1'):45,
    ('churchgate_1','churchgate_2'):18,
    ('churchgate_2','churchgate_3'):20,
    ('churchgate_3','churchgate_4'):22,
    ('churchgate_4','churchgate_1'):25,
}


class CoordinationManager:
    """
    Manages green wave coordination between neighboring signals.
    When signal A goes green on a road-facing lane,
    it tells its downstream neighbor B to prepare:
      "I'm going green now for Xs, you should go green in Ys"
    where Y = travel time from A to B.
    """

    def __init__(self):
        self.green_wave_requests: Dict[str, dict] = {}
        # signal_id → {requested_at, offset_seconds, requesting_signal, lane}
        self.coordination_log = []

    def get_neighbors(self, signal_id: str) -> List[str]:
        return SIGNAL_NEIGHBORS.get(signal_id, [])

    def get_travel_time(self, from_id: str, to_id: str) -> int:
        return (TRAVEL_TIMES.get((from_id, to_id)) or
                TRAVEL_TIMES.get((to_id, from_id)) or 25)

    def notify_green(self, signal_id: str, lane: str, green_duration: int):
        """
        Called when a signal goes green.
        Notifies downstream neighbors to prepare their green wave.
        """
        neighbors = self.get_neighbors(signal_id)
        now       = time.time()

        for neighbor_id in neighbors:
            travel  = self.get_travel_time(signal_id, neighbor_id)
            # Neighbor should go green when vehicles arrive from this signal
            go_at   = now + travel

            if neighbor_id not in self.green_wave_requests:
                self.green_wave_requests[neighbor_id] = {
                    'requested_at':      now,
                    'go_green_at':       go_at,
                    'travel_time':       travel,
                    'requesting_signal': signal_id,
                    'lane':              lane,
                    'green_duration':    green_duration,
                }
                print(f"🌊 Green wave: {signal_id} → {neighbor_id} "
                      f"(vehicles arrive in {travel}s, lane={lane})")

                self.coordination_log.append({
                    'from':    signal_id,
                    'to':      neighbor_id,
                    'lane':    lane,
                    'offset':  travel,
                    'time':    now,
                })
                # Keep log small
                if len(self.coordination_log) > 100:
                    self.coordination_log.pop(0)

    def should_prepare_green(self, signal_id: str) -> Optional[dict]:
        """
        Check if this signal should prepare for a green wave.
        Returns the wave request if it's time to act, None otherwise.
        """
        req = self.green_wave_requests.get(signal_id)
        if not req:
            return None

        now = time.time()
        # Prepare 3 seconds before vehicles arrive
        if now >= req['go_green_at'] - 3:
            del self.green_wave_requests[signal_id]
            return req

        return None

    def get_neighbor_load(self, signal_id: str, all_states: dict) -> float:
        """
        Get average vehicle load of neighboring signals.
        Used as input to DQN state.
        """
        neighbors = self.get_neighbors(signal_id)
        if not neighbors:
            return 0.0

        loads = []
        for nid in neighbors:
            if nid in all_states:
                counts = all_states[nid].get('vehicle_counts', {})
                total  = sum(counts.values()) if counts else 0
                loads.append(total)

        return sum(loads) / len(loads) if loads else 0.0

    def get_status(self) -> dict:
        return {
            'pending_waves':    len(self.green_wave_requests),
            'wave_requests':    {
                k: {
                    'from':         v['requesting_signal'],
                    'lane':         v['lane'],
                    'arrives_in':   max(0, round(v['go_green_at'] - time.time())),
                }
                for k, v in self.green_wave_requests.items()
            },
            'recent_waves':     self.coordination_log[-5:],
        }


# Singleton
_coord_manager = CoordinationManager()

def get_coordinator() -> CoordinationManager:
    return _coord_manager