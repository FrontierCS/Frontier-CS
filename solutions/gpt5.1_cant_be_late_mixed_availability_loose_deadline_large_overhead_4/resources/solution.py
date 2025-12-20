from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_hedging_v1"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = self.env

        elapsed = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        gap = float(getattr(env, "gap_seconds", 0.0) or 0.0)

        time_left = deadline - elapsed

        # Conservative requirement: time needed to finish the entire task on on-demand,
        # assuming no progress has been made yet, plus one gap for discretization safety.
        required_time_for_safe_on_demand = task_duration + restart_overhead + gap

        # If we don't have enough slack to risk losing another gap to spot/idle,
        # switch to on-demand and stay there until completion.
        if time_left <= required_time_for_safe_on_demand:
            return ClusterType.ON_DEMAND

        # In the slack region: use spot whenever available; otherwise pause (free) and wait.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
