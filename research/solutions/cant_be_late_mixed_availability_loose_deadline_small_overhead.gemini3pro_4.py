from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "DeadlineAwareSlackStrategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the strategy.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide which cluster type to use based on deadline constraints and cost.
        """
        # Calculate total work done and remaining
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If work is complete, do nothing
        if work_remaining <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        
        # Calculate Safety Margin
        # We use a buffer of 3 * gap_seconds to handle simulation step granularity and 
        # ensure we don't miss the deadline due to floating point rounding or off-by-one errors.
        buffer = 3.0 * self.env.gap_seconds

        # Calculate Panic Threshold (Latest Safe Start Time)
        # This is the latest time by which we MUST be running reliably (On-Demand) to finish.
        # We subtract the restart_overhead to account for the time lost if we need to 
        # switch from NONE/SPOT to ON_DEMAND.
        # If we are already ON_DEMAND, this conservative threshold effectively keeps us 
        # on ON_DEMAND with a small extra safety margin (the overhead time).
        
        # Time required to finish = Work Remaining + Restart Overhead + Buffer
        # Panic Threshold = Deadline - Time required
        panic_threshold = self.deadline - (work_remaining + self.restart_overhead + buffer)

        # 1. Critical Phase: No slack left
        if current_time >= panic_threshold:
            return ClusterType.ON_DEMAND

        # 2. Slack Phase: Optimization
        # If we have slack, we want to minimize cost.
        # - ClusterType.SPOT is the cheapest option (~1/3 of OD).
        # - ClusterType.NONE is free (0 cost).
        # - ClusterType.ON_DEMAND is expensive.
        #
        # Strategy:
        # If Spot is available, use it aggressively to progress the task cheaply.
        # If Spot is NOT available, prefer waiting (NONE) over On-Demand. 
        # Waiting costs 'slack' (time) but saves money. Since we are below the 
        # panic_threshold, we have slack to burn.
        
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)