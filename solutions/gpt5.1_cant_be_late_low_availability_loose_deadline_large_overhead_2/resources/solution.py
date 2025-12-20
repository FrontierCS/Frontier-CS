from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_static_fallback_v1"

    def __init__(self, args):
        super().__init__(args)
        self._required_fallback_time = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _initialize_policy(self):
        if self._required_fallback_time is None:
            restart_overhead = getattr(self, "restart_overhead", 0.0)
            self._required_fallback_time = self.task_duration + restart_overhead

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_policy()

        t = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        deadline = self.deadline
        required_fallback = self._required_fallback_time

        time_remaining_after_step = deadline - (t + gap)
        safe_to_risk = time_remaining_after_step >= required_fallback

        if safe_to_risk:
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.NONE

        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
