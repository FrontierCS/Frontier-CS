from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "Lazy_Deadline_Constraint"

    def solve(self, spec_path: str) -> "Solution":
        """
        No initialization required for this strategy.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decides the cluster type for the next step based on deadlines and cost.
        """
        # Current state
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        total_work = self.task_duration
        done_work = sum(self.task_done_time)
        work_rem = max(0.0, total_work - done_work)
        
        # If task is complete, do nothing
        if work_rem <= 0:
            return ClusterType.NONE

        time_rem = deadline - elapsed
        R = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Safety buffer: 2 time steps to account for discrete simulation boundaries
        buffer = 2.0 * gap
        
        # Check Criticality: Do we HAVE to run On-Demand to meet the deadline?
        # If we are currently On-Demand, we don't pay overhead to continue.
        # If we are Spot or None, we must pay 'R' to switch to On-Demand.
        is_od = (last_cluster_type == ClusterType.ON_DEMAND)
        
        threshold = work_rem + buffer
        if not is_od:
            threshold += R
            
        # If remaining time is tight, force On-Demand to guarantee completion
        if time_rem <= threshold:
            return ClusterType.ON_DEMAND
            
        # Not Critical: Optimize for Cost
        if has_spot:
            # Spot is available.
            # If we are currently On-Demand, switching to Spot incurs overhead R.
            # It's only worth switching if the remaining work is long enough to offset the overhead cost.
            # Heuristic: Price_OD ~ 3 * Price_Spot. 
            # Break-even: 1*(Work + R) < 3*Work => R < 2*Work => Work > R/2.
            # We use 0.55 * R as a conservative threshold.
            if is_od and work_rem < (R * 0.55):
                return ClusterType.ON_DEMAND
            
            return ClusterType.SPOT
        else:
            # Spot is unavailable, but we have slack (not critical).
            # Wait (NONE) to save money.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)