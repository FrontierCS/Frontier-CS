from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work
        current_progress = sum(self.task_done_time)
        remaining_work = self.task_duration - current_progress

        # If task is effectively complete, stop
        if remaining_work <= 0:
            return ClusterType.NONE

        # Current simulation state
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        time_left = deadline - elapsed
        gap = self.env.gap_seconds
        restart_overhead = self.restart_overhead

        # Safety Logic:
        # Determine the latest point we must switch to On-Demand to guarantee completion.
        # We assume that if we are not running effectively on OD, we will incur overhead to start it.
        # Even if we are currently on OD, checking against the overhead-included threshold
        # ensures we don't switch off OD unless we have enough slack to pay the overhead to come back.
        
        # We need to ensure that at the NEXT time step (elapsed + gap), we still have enough time.
        # Time required to finish reliably = remaining_work + restart_overhead
        # We add a buffer (2.0 * gap) to handle simulation discretization and floating point margins.
        
        safe_threshold = remaining_work + restart_overhead + gap + (2.0 * gap)

        # 1. Critical Phase: If we are close to the deadline, force On-Demand.
        # This takes precedence over everything to avoid the -100,000 penalty.
        if time_left <= safe_threshold:
            return ClusterType.ON_DEMAND

        # 2. Economic Phase: We have slack. Optimize for cost.
        if has_spot:
            # Spot is available and we have time to handle interruptions.
            return ClusterType.SPOT
        else:
            # Spot is unavailable, but we have slack.
            # We choose to wait (NONE) rather than burn expensive On-Demand hours.
            # The safety threshold ensures we will switch to OD before it's too late.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)