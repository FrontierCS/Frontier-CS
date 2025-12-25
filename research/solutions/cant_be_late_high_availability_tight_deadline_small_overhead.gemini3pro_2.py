from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        # Calculate remaining work
        # task_done_time is a list of segments completed
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining_work = self.task_duration - done
        
        if remaining_work <= 1e-6:
            return ClusterType.NONE
            
        # Calculate time left until the hard deadline
        time_left = self.deadline - elapsed
        
        # Calculate the time required if we commit to ON_DEMAND right now.
        # If we are not currently on ON_DEMAND, we incur a restart overhead to switch/start it.
        # Even if we are on SPOT, switching to ON_DEMAND is treated as a new instance.
        switch_cost = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            switch_cost = self.restart_overhead
            
        needed_on_od = remaining_work + switch_cost
        
        # Slack is the buffer we have before we MUST run on ON_DEMAND to finish in time.
        slack = time_left - needed_on_od
        
        # Determine a safety margin.
        # We need to ensure that if we wait/use Spot this step, we can still switch to OD 
        # in the next step (elapsed + gap) without violating the deadline.
        # We use a robust buffer of 15 minutes or 3 time steps.
        buffer = max(15 * 60, 3 * gap)
        
        # Critical Path: If slack is running out, we must switch to reliable ON_DEMAND.
        if slack < buffer:
            return ClusterType.ON_DEMAND
            
        # Cost Optimization: Use Spot if available.
        if has_spot:
            return ClusterType.SPOT
            
        # If Spot is unavailable but we have plenty of slack, wait (NONE) to save money.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)