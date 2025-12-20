from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self._committed_to_od = False
        self._safety_margin_seconds = None
        self._restart_overhead_buffer = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _initialize_margins_if_needed(self):
        if self._safety_margin_seconds is not None:
            return
        gap = getattr(self.env, "gap_seconds", 60.0)
        restart_overhead = getattr(self, "restart_overhead", 0.0)
        # Safety margin must be at least one time step to avoid discretization issues.
        # Also keep at least some buffer; 600s is a reasonable minimum.
        self._safety_margin_seconds = max(restart_overhead, gap, 600.0)
        self._restart_overhead_buffer = restart_overhead

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_margins_if_needed()

        # Total useful work completed so far.
        progress = sum(self.task_done_time)
        remaining_work = max(self.task_duration - progress, 0.0)

        # If the task is already finished, do nothing.
        if remaining_work <= 0.0:
            self._committed_to_od = False
            return ClusterType.NONE

        now = self.env.elapsed_seconds
        time_left = self.deadline - now

        # Once we commit to on-demand, we never go back to spot.
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Conservative upper bound on time needed to finish if we switch to OD now.
        need_time = remaining_work + self._restart_overhead_buffer

        # If we don't have enough slack to keep gambling on spot, commit to OD.
        if time_left <= need_time + self._safety_margin_seconds:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Pre-commit phase: use spot when available, otherwise idle to save cost.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
