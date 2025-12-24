from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        self.args = args
        self._committed_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _total_done(self) -> float:
        try:
            if self.task_done_time:
                return float(sum(self.task_done_time))
        except Exception:
            pass
        return 0.0

    def _remaining_work(self) -> float:
        try:
            rem = float(self.task_duration) - self._total_done()
            return rem if rem > 0.0 else 0.0
        except Exception:
            return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to on-demand, stay there.
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        remaining = self._remaining_work()
        if remaining <= 0.0:
            return ClusterType.NONE

        # Compute slack and conservative margin.
        now = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        slack = max(0.0, deadline - now)

        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        # Fudge accounts for discretization and sim timing
        fudge = min(max(2.0 * gap, 60.0), 900.0)  # clamp between 1 min and 15 min

        # If we switch to OD now, assume worst-case we must pay one restart overhead
        # unless we're already on OD.
        try:
            restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        except Exception:
            restart_overhead = 0.0

        overhead_if_commit = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead

        # Commit threshold: ensure we can finish on OD by the deadline with margin.
        if slack <= remaining + overhead_if_commit + fudge:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, prefer spot if available; else wait to preserve budget until we must commit.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
