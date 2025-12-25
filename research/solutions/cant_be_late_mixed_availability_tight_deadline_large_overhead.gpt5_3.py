from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args
        self.committed_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _total_done(self) -> float:
        done = getattr(self, "task_done_time", 0.0)
        if isinstance(done, (int, float)):
            try:
                return float(done)
            except Exception:
                return 0.0
        try:
            return float(sum(done))
        except Exception:
            return 0.0

    def _remaining_work(self) -> float:
        try:
            duration = float(self.task_duration)
        except Exception:
            duration = 0.0
        done = self._total_done()
        rem = duration - done
        return rem if rem > 0.0 else 0.0

    def _time_left(self) -> float:
        try:
            return max(float(self.deadline) - float(self.env.elapsed_seconds), 0.0)
        except Exception:
            return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to OD, keep using OD
        if self.committed_to_od:
            return ClusterType.ON_DEMAND

        remaining_work = self._remaining_work()
        if remaining_work <= 0.0:
            return ClusterType.NONE

        try:
            gap = float(self.env.gap_seconds)
        except Exception:
            gap = 60.0
        try:
            R = float(self.restart_overhead)
        except Exception:
            R = 0.0

        time_left = self._time_left()

        # Overhead if we switch to OD now (0 if already on OD)
        od_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else R
        od_time_needed = remaining_work + od_overhead

        # Safety margin: cover one decision step latency + small cushion on overhead
        margin = gap + 0.25 * R + 60.0

        # If we don't have enough time to gamble anymore, commit to OD
        if time_left <= od_time_needed + margin:
            self.committed_to_od = True
            return ClusterType.ON_DEMAND

        # If spot is available, prefer spot, but avoid starting a brand new spot too close to deadline
        if has_spot:
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            else:
                # Guard against starting SPOT when near OD-commit boundary.
                # Require extra slack approximately equal to paying one extra spot restart overhead.
                start_spot_guard = R + gap
                if time_left > od_time_needed + margin + start_spot_guard:
                    return ClusterType.SPOT
                else:
                    self.committed_to_od = True
                    return ClusterType.ON_DEMAND

        # Spot unavailable: decide to wait or switch to OD
        slack = time_left - (od_time_needed + margin)
        if slack > 0.0:
            return ClusterType.NONE
        else:
            self.committed_to_od = True
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)