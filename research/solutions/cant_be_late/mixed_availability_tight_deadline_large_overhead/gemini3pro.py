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
        # Calculate amount of work remaining
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        # If task is logically complete, stop
        if remaining_work <= 0:
            return ClusterType.NONE

        # Calculate time remaining until hard deadline
        elapsed_time = self.env.elapsed_seconds
        time_left = self.deadline - elapsed_time
        
        # Slack is the time buffer we have; if slack <= 0, we can barely finish even with perfect availability
        slack = time_left - remaining_work
        
        # Define a panic threshold. If slack falls below this, we must use On-Demand to guarantee completion.
        # We need to account for:
        # 1. Restart overhead (time lost spinning up an instance)
        # 2. Step size (gap_seconds) to ensure we don't miss the decision point
        # 3. A safety margin
        # 3.0x overhead ensures we have ample time to incur the restart penalty and still finish.
        # 1.5x gap_seconds ensures robustness against large time steps.
        threshold = (3.0 * self.restart_overhead) + (1.5 * self.env.gap_seconds)
        
        # If we are running out of slack, force On-Demand usage.
        if slack < threshold:
            return ClusterType.ON_DEMAND
            
        # If we have slack and Spot is available, use Spot (cheapest option).
        if has_spot:
            return ClusterType.SPOT
            
        # If Spot is unavailable but we have plenty of slack, wait (NONE).
        # This saves money compared to running On-Demand immediately.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)