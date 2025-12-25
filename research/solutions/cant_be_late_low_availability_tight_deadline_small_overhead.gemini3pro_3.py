from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        deadline = self.deadline
        duration = self.task_duration
        overhead = self.restart_overhead
        
        work_done = sum(self.task_done_time) if self.task_done_time else 0.0
        work_rem = duration - work_done
        time_rem = deadline - elapsed
        
        # If task is completed
        if work_rem <= 1e-6:
            return ClusterType.NONE
            
        slack = time_rem - work_rem
        
        # Calculate critical slack threshold.
        # We must maintain enough slack to:
        # 1. Absorb a failed step (gap) if Spot is preempted/unavailable
        # 2. Pay the restart overhead to switch to On-Demand
        # 3. Include a small safety margin
        critical_slack = overhead + gap + (overhead * 0.2)
        
        # Threshold to switch from On-Demand back to Spot.
        # We require significantly more slack to justify the switch cost/risk.
        spot_entry_slack = critical_slack + (overhead * 4.0)
        
        # 1. Safety Constraint: If slack is too low, force On-Demand to guarantee completion.
        if slack < critical_slack:
            return ClusterType.ON_DEMAND
            
        # 2. Availability Constraint: If Spot is unavailable, use On-Demand.
        # Waiting (NONE) is too risky given the strict deadline and high penalty.
        if not has_spot:
            return ClusterType.ON_DEMAND
            
        # 3. Cost Minimization
        # Spot is available and we have sufficient slack.
        if last_cluster_type == ClusterType.ON_DEMAND:
            # Hysteresis: Only switch back to Spot if we have ample slack
            if slack > spot_entry_slack:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        else:
            # Currently on Spot or None, and safe to proceed with Spot
            return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)