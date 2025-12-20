from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_spot"

    def __init__(self, args):
        super().__init__(args)
        self.locked_to_od = False
        self._init_done = False
        self._extra_slack_seconds = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _initialize_if_needed(self):
        if self._init_done:
            return
        self._init_done = True
        # Extra safety slack beyond restart_overhead and discretization
        # 30 minutes in seconds
        self._extra_slack_seconds = 30 * 60.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_if_needed()

        # Compute remaining work (in seconds)
        done = 0.0
        if self.task_done_time:
            done = sum(self.task_done_time)
        remaining_work = max(self.task_duration - done, 0.0)

        # If task is already done, no need to run anything.
        if remaining_work <= 0:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        time_to_deadline = self.deadline - elapsed

        # Restart overhead (in seconds); be robust if attribute missing
        restart_overhead = getattr(self, "restart_overhead", 0.0)

        # Time required to safely complete purely on on-demand from now:
        # remaining work + one restart overhead + discretization and safety buffer.
        buffer = restart_overhead + 2.0 * gap + self._extra_slack_seconds
        fallback_time = remaining_work + buffer

        # Lock into on-demand mode once we approach the deadline enough
        if (not self.locked_to_od) and (time_to_deadline <= fallback_time):
            self.locked_to_od = True

        if self.locked_to_od:
            return ClusterType.ON_DEMAND

        # Not yet locked to on-demand: be aggressive with spot.
        if has_spot:
            return ClusterType.SPOT

        # Spot not available and we still have slack: wait (no cost).
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
