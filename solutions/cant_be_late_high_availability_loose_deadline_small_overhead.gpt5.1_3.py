from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_slack_fallback"

    def solve(self, spec_path: str) -> "Solution":
        # Initialize any state here
        self.fallback_committed = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Ensure state exists even if solve() was not called
        if not hasattr(self, "fallback_committed"):
            self.fallback_committed = False

        # If task already effectively done, don't run any instances
        remaining_work = max(0.0, self.task_duration - sum(self.task_done_time))
        if remaining_work <= 0:
            self.fallback_committed = True
            return ClusterType.NONE

        remaining_time = max(0.0, self.deadline - self.env.elapsed_seconds)
        H = float(self.restart_overhead)
        dt = float(self.env.gap_seconds)

        # If we've already committed to on-demand, keep using it
        if self.fallback_committed:
            return ClusterType.ON_DEMAND

        # Time needed to finish if we switch to on-demand now (worst-case)
        needed_time = remaining_work + H

        # If waiting or using spot for another step could make it impossible
        # to finish on on-demand alone, commit to on-demand now.
        if remaining_time <= needed_time + dt:
            self.fallback_committed = True
            return ClusterType.ON_DEMAND

        # We still have enough slack to safely use spot / wait for spot
        if has_spot:
            return ClusterType.SPOT

        # No spot available and enough slack: wait (no cost this step)
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
