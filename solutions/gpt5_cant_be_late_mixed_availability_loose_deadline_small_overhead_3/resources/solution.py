from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_guard_bang_bang_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self.args = args
        self._committed_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _should_commit_to_on_demand(self) -> bool:
        # Commit to On-Demand when we reach the latest safe start time:
        # deadline - task_duration - restart_overhead - gap_seconds (safety margin for discretization)
        # All units are in seconds.
        elapsed = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
        deadline = getattr(self, "deadline", 0.0) or 0.0
        task_duration = getattr(self, "task_duration", 0.0) or 0.0
        restart_overhead = getattr(self, "restart_overhead", 0.0) or 0.0

        # Safety margin: one gap step to account for decision discretization + one restart overhead to start OD
        safety_margin = restart_overhead + gap

        latest_safe_start = deadline - task_duration - safety_margin
        return elapsed >= latest_safe_start

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Once committed to On-Demand, stay on it to ensure deadline.
        if not self._committed_to_od and self._should_commit_to_on_demand():
            self._committed_to_od = True

        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Before commitment time:
        # - Use SPOT if available (cheap).
        # - Otherwise pause to conserve budget; slack ensures feasibility.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
