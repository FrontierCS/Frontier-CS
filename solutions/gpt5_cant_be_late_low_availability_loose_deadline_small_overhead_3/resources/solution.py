from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_hybrid_v2"

    def __init__(self, args=None):
        super().__init__(args)
        self._commit_to_on_demand = False
        self._base_margin_seconds = 600  # 10 minutes buffer
        self._min_margin_seconds = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _current_margin(self) -> float:
        # Dynamic margin: ensure some slack for overhead and step granularity
        gap = getattr(self.env, "gap_seconds", 60.0) or 60.0
        overhead = getattr(self, "restart_overhead", 180.0) or 180.0
        base = max(self._base_margin_seconds, 2 * gap, overhead)
        return max(base, self._min_margin_seconds)

    def _remaining_work(self) -> float:
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining = max(0.0, self.task_duration - done)
        return remaining

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining = self._remaining_work()
        if remaining <= 0:
            return ClusterType.NONE

        now = self.env.elapsed_seconds
        time_left = self.deadline - now
        if time_left <= 0:
            self._commit_to_on_demand = True
            return ClusterType.ON_DEMAND

        margin = self._current_margin()

        # If we've already committed to on-demand, stick with it to avoid thrashing
        if self._commit_to_on_demand:
            return ClusterType.ON_DEMAND

        # Decide if we must start on-demand now to meet deadline even in worst case
        # We need at least (remaining + overhead_to_switch + margin) seconds left
        overhead_to_switch = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead
        must_switch_to_od = time_left <= (remaining + overhead_to_switch + margin)

        if must_switch_to_od:
            self._commit_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Otherwise, try to use spot if available; else wait if we can afford it
        if has_spot:
            return ClusterType.SPOT

        # Spot is unavailable: wait if we still have slack; else commit to on-demand
        # Safe to wait if after waiting arbitrarily long, we still can commit and finish.
        # This holds as long as time_left > (remaining + restart_overhead + margin).
        if time_left > (remaining + self.restart_overhead + margin):
            return ClusterType.NONE

        # Not safe to keep waiting -> commit to on-demand
        self._commit_to_on_demand = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
