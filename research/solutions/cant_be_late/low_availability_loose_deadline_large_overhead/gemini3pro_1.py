from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.
        """
        # Calculate progress and remaining work
        # task_done_time is a list of completed work segment durations
        progress = sum(self.task_done_time)
        remaining_work = self.task_duration - progress
        
        # If the task is effectively done, stop incurring costs
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # SAFETY CHECK:
        # We must ensure we finish before the deadline.
        # Calculate the minimum time required to finish if we switch to On-Demand (OD) now.
        # This includes the actual work time plus the restart overhead to spin up the OD instance.
        min_time_required = remaining_work + overhead
        
        # Calculate a safety buffer.
        # We need to account for:
        # 1. The current time step duration (gap), which might be "wasted" if we choose Spot and it fails.
        # 2. Additional overhead margin to handle potential transition costs safely.
        # 3. A robust multiplier to prevent deadline violations (penalty -100,000).
        # Buffer = 2 * overhead + 5 * gap ensures we can survive a failed Spot attempt and still have time to restart OD.
        safety_buffer = 2.0 * overhead + 5.0 * gap
        
        # If we are within the panic threshold, force On-Demand usage.
        if time_left < (min_time_required + safety_buffer):
            return ClusterType.ON_DEMAND

        # COST OPTIMIZATION:
        # If we have plenty of slack (time_left is large), we aim to minimize cost.
        
        if has_spot:
            # If Spot is available, use it (cheapest option).
            return ClusterType.SPOT
        else:
            # If Spot is unavailable but we still have slack, DO NOT use OD yet.
            # Waiting (NONE) costs $0. Using OD costs ~$3.
            # By waiting, we preserve the option to use Spot later when it becomes available.
            # The Safety Check above guarantees we won't wait too long.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)