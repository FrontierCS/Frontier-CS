from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "safe_spot_fallback_v1"

    def __init__(self, args):
        super().__init__(args)

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = getattr(self, "env", None)

        deadline = getattr(self, "deadline", None)
        task_duration = getattr(self, "task_duration", None)
        restart_overhead = getattr(self, "restart_overhead", 0.0)

        gap = getattr(env, "gap_seconds", 60.0) if env is not None else 60.0
        now = getattr(env, "elapsed_seconds", 0.0) if env is not None else 0.0

        # If we don't know the job specs, be conservative and use on-demand.
        if deadline is None or task_duration is None:
            return ClusterType.ON_DEMAND

        # Total slack time available (seconds).
        slack = max(0.0, deadline - task_duration)

        # If there is no slack, must always use on-demand.
        if slack <= 0.0:
            return ClusterType.ON_DEMAND

        # Safety margin to account for restart overhead and discretization.
        # Cap the safety margin to at most 25% of slack so we still use spot meaningfully.
        base_margin = max(1800.0, 5.0 * gap, 2.0 * restart_overhead)  # at least 30 min, or based on gap/overhead
        max_margin = slack * 0.25
        safety_margin = base_margin if base_margin < max_margin else max_margin

        # Latest safe time to start a final uninterrupted on-demand run from (worst-case no prior progress).
        fallback_time = deadline - task_duration - restart_overhead - safety_margin
        if fallback_time < 0.0:
            fallback_time = 0.0

        # After fallback_time, always use on-demand to guarantee completion.
        if now >= fallback_time:
            return ClusterType.ON_DEMAND

        # Before fallback window: use spot when available, otherwise stay idle to save cost.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)