from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "DeadlineAwareCostMinimizer"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decides the cluster type for the next time step.
        """
        # Calculate work done and remaining
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If task is already done, do nothing
        if work_remaining <= 0:
            return ClusterType.NONE

        # Current time status
        current_time = self.env.elapsed_seconds
        time_left = self.deadline - current_time
        
        # Calculate the deadline safety threshold.
        # We must switch to On-Demand (OD) if the remaining time is close to the minimum time required
        # to finish the job using OD.
        # Minimum time = Remaining Work + Restart Overhead (to launch OD).
        # We add a safety buffer of 2 * gap_seconds to account for the discrete time stepping of the simulation.
        # This ensures that even if we wait this step, we will catch the deadline constraint at the next step.
        safety_buffer = 2.0 * self.env.gap_seconds
        required_time_od = work_remaining + self.restart_overhead + safety_buffer

        # CRITICAL: If we are near the point of no return, force On-Demand usage.
        # This guarantees we finish before the deadline (avoiding the massive penalty).
        if time_left <= required_time_od:
            return ClusterType.ON_DEMAND

        # OPTIMIZATION: If we have enough slack time, minimize cost.
        # Spot instances are cheaper.
        if has_spot:
            return ClusterType.SPOT
        
        # If Spot is unavailable but we are not yet in the critical window,
        # pause execution (NONE) to wait for Spot availability and save money compared to OD.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
