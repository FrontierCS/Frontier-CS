from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_guard_spot_v2"

    def solve(self, spec_path: str) -> "Solution":
        self._od_committed = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not hasattr(self, "_od_committed"):
            self._od_committed = False

        # If we've committed to on-demand, keep running on-demand to avoid overheads and risks
        if self._od_committed:
            return ClusterType.ON_DEMAND

        # Compute remaining work
        done = sum(self.task_done_time) if getattr(self, "task_done_time", None) else 0.0
        remaining = max(0.0, self.task_duration - done)

        # If task is already done, do nothing
        if remaining <= 0:
            return ClusterType.NONE

        # Time left to deadline
        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0:
            # Extremely late; attempt to run on-demand anyway
            self._od_committed = True
            return ClusterType.ON_DEMAND

        gap = self.env.gap_seconds
        # Small epsilon to account for discretization and rounding
        epsilon = 1.0  # seconds

        # If we wait or run spot for one more step and make zero progress (worst-case),
        # can we still finish by switching to OD next step?
        # Overhead when switching to OD from SPOT/NONE at next step.
        overhead_next = self.restart_overhead

        can_wait_one_step = (time_left - gap) >= (remaining + overhead_next + epsilon)

        if not can_wait_one_step:
            # Not safe to wait; commit to on-demand now
            self._od_committed = True
            return ClusterType.ON_DEMAND

        # Safe to wait one more step
        if has_spot:
            # Prefer spot when available
            # If we were already on OD (shouldn't happen since committed flag), keep OD
            if last_cluster_type == ClusterType.ON_DEMAND and self._od_committed:
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # Spot unavailable; wait to preserve budget
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)