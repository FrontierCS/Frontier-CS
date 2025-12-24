from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_v1"

    def solve(self, spec_path: str) -> "Solution":
        # Optional initialization hook; we just ensure our state fields exist.
        self._spec_path = spec_path
        if not hasattr(self, "committed_to_on_demand"):
            self.committed_to_on_demand = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Ensure state initialization (in case solve() wasn't called).
        if not hasattr(self, "committed_to_on_demand"):
            self.committed_to_on_demand = False

        # If we've already committed to always use on-demand, stick with it.
        if self.committed_to_on_demand:
            return ClusterType.ON_DEMAND

        # Compute total completed work in seconds.
        if self.task_done_time:
            done = sum(self.task_done_time)
        else:
            done = 0.0

        remaining_work = max(self.task_duration - done, 0.0)
        # If no remaining work, do nothing.
        if remaining_work <= 0:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds

        # Latest safe time to *start* an on-demand run that will
        # definitely finish before the deadline, assuming:
        #     start_time + restart_overhead + remaining_work <= deadline
        latest_start_time = self.deadline - self.restart_overhead - remaining_work

        # Decide whether it's still safe to wait one more step before
        # switching to on-demand (worst case: zero progress during the step).
        # We require that at the *next* decision point we can still start
        # on-demand and finish by the deadline.
        safe_to_wait = (elapsed + gap) <= latest_start_time

        if not safe_to_wait:
            # We must commit to on-demand now to maintain the deadline guarantee.
            self.committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # We're safely early: use spot when available, otherwise idle to save cost.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
