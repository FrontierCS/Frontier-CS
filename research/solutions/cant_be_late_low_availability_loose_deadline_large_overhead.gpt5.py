from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "safe_fallback_buffered"

    def __init__(self, args=None):
        super().__init__(args)
        self._od_lock = False
        self._od_lock_time = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _progress_seconds(self) -> float:
        if hasattr(self, "task_done_time") and self.task_done_time:
            try:
                return float(sum(self.task_done_time))
            except Exception:
                return 0.0
        return 0.0

    def _remaining_work(self) -> float:
        progress = self._progress_seconds()
        if hasattr(self, "task_duration"):
            return max(0.0, float(self.task_duration) - progress)
        return 0.0

    def _time_left(self) -> float:
        try:
            return float(self.deadline) - float(self.env.elapsed_seconds)
        except Exception:
            return 0.0

    def _guard_seconds(self) -> float:
        try:
            gap = float(self.env.gap_seconds)
        except Exception:
            gap = 60.0
        try:
            ro = float(self.restart_overhead)
        except Exception:
            ro = 0.0
        # Buffer to account for step discretization and timing uncertainties
        return max(2.0 * gap, min(ro, 3.0 * gap))

    def _should_lock_to_od(self) -> bool:
        # If we've already locked, keep it
        if self._od_lock:
            return True
        time_left = self._time_left()
        work_left = self._remaining_work()
        guard = self._guard_seconds()
        try:
            ro = float(self.restart_overhead)
        except Exception:
            ro = 0.0
        # If remaining time is tight, lock to OD
        return time_left <= work_left + ro + guard

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If task already done, do nothing
        if self._remaining_work() <= 0.0:
            return ClusterType.NONE

        # If we've locked to OD previously, keep using OD
        if self._od_lock:
            return ClusterType.ON_DEMAND

        # Decide if we must lock to OD now to meet the deadline
        if self._should_lock_to_od():
            self._od_lock = True
            self._od_lock_time = getattr(self.env, "elapsed_seconds", None)
            return ClusterType.ON_DEMAND

        # Otherwise, prefer SPOT when available, else wait (NONE) to save cost
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)