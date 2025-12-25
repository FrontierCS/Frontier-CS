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
            except TypeError:
                pass
        self.args = args
        self.lock_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _progress_seconds(self) -> float:
        gap = getattr(self.env, "gap_seconds", 60.0) or 60.0
        times = getattr(self, "task_done_time", None)
        if not times:
            return 0.0
        # Use length-based progress as robust estimator; overhead doesn't add to progress.
        progress_by_len = len(times) * gap
        try:
            sum_times = float(sum(times)) if times else 0.0
        except Exception:
            sum_times = float("inf")
        progress = min(progress_by_len, sum_times)
        td = getattr(self, "task_duration", None)
        if td is None:
            return progress_by_len
        return min(progress, td)

    def _remaining_work(self) -> float:
        td = getattr(self, "task_duration", 0.0) or 0.0
        done = self._progress_seconds()
        remain = td - done
        return remain if remain > 0 else 0.0

    def _time_left(self) -> float:
        deadline = getattr(self, "deadline", 0.0) or 0.0
        elapsed = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
        left = deadline - elapsed
        return left if left > 0 else 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we've already committed to on-demand, keep using it to avoid extra restarts.
        if self.lock_od:
            return ClusterType.ON_DEMAND

        gap = getattr(self.env, "gap_seconds", 60.0) or 60.0
        restart_overhead = getattr(self, "restart_overhead", 0.0) or 0.0

        remaining_work = self._remaining_work()
        if remaining_work <= 0:
            return ClusterType.NONE

        time_left = self._time_left()

        # Safety buffer to account for discretization and minor uncertainties.
        safety_fudge = max(gap, 60.0)

        # Latest time to start OD such that OD finishes within deadline including one restart overhead.
        # Commit to OD when we reach/past this threshold.
        must_commit = time_left <= (remaining_work + restart_overhead + safety_fudge)

        if must_commit:
            self.lock_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, we can still try to use spot if available; if not, wait (NONE).
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)