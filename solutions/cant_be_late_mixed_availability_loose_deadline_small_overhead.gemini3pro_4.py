from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "cant_be_late_strategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize strategy. Returns self.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decides which cluster type to use at the current step.
        """
        # Calculate remaining work in seconds
        # task_done_time is a list of completed segment durations
        work_done = sum(self.task_done_time) if self.task_done_time else 0.0
        work_remaining = self.task_duration - work_done
        
        # If work is completed, do nothing
        if work_remaining <= 0:
            return ClusterType.NONE

        # Calculate time remaining until deadline
        time_elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - time_elapsed
        
        # Calculate the overhead required to switch to On-Demand
        # If we are already on OD, we continue with 0 overhead.
        # If we are on SPOT or NONE, we incur restart_overhead to start OD.
        switch_overhead = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            switch_overhead = self.restart_overhead
            
        # Define a safety buffer to account for:
        # 1. Discrete time steps (gap_seconds)
        # 2. Potential uncommitted work lost during a forced restart
        # 3. General variance
        # 30 minutes (1800s) + 2 steps is a conservative buffer given the high penalty.
        buffer = 1800.0 + (2.0 * self.env.gap_seconds)
        
        # Critical Threshold Logic:
        # If the remaining wall-clock time is approaching the bare minimum needed 
        # to finish the job using reliable On-Demand instances, we must switch now.
        required_time_on_od = work_remaining + switch_overhead + buffer
        
        if time_remaining <= required_time_on_od:
            return ClusterType.ON_DEMAND
            
        # If we are not in the critical zone (we have slack):
        # 1. Use Spot if available (cheapest option)
        if has_spot:
            return ClusterType.SPOT
            
        # 2. If Spot is unavailable, wait (NONE).
        # We prefer waiting over paying for OD because we still have slack.
        # This allows us to wait for Spot availability to return.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
