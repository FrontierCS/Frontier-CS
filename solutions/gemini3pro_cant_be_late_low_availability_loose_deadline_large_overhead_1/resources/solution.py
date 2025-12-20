from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "Solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Retrieve environment state
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        deadline = self.deadline
        overhead = self.restart_overhead
        total_duration = self.task_duration
        
        # Calculate work done and remaining work
        # task_done_time is a list of durations of completed segments
        work_done = sum(self.task_done_time)
        remaining_work = max(0.0, total_duration - work_done)
        
        # If task is effectively complete, pause (env usually handles termination)
        if remaining_work <= 1e-6:
            return ClusterType.NONE
            
        time_left = deadline - elapsed
        
        # Panic Threshold Calculation
        # We determine the latest possible time we can switch to On-Demand (OD)
        # to guarantee finishing before the deadline.
        #
        # Components of the required time:
        # 1. remaining_work: Actual compute time needed.
        # 2. overhead: Time lost to initialization/restart. We include this even if 
        #    currently running OD to ensure we don't switch away from OD when close to deadline (hysteresis).
        # 3. Safety Buffer:
        #    - 2.0 * gap: Account for the discrete decision interval (we might be 'gap' seconds late in reacting).
        #    - 0.1 * overhead: Additional margin for simulation variances.
        
        safety_buffer = (2.0 * gap) + (0.1 * overhead)
        must_start_od_time = remaining_work + overhead + safety_buffer
        
        # Decision Logic
        
        # 1. Deadline Safety Override:
        # If we are approaching the point of no return, force usage of On-Demand.
        if time_left <= must_start_od_time:
            return ClusterType.ON_DEMAND
            
        # 2. Cost Optimization:
        # If we have slack (time_left > must_start_od_time):
        if has_spot:
            # Prefer Spot instances to minimize cost
            return ClusterType.SPOT
        else:
            # If Spot is unavailable but we have slack, wait (NONE).
            # Waiting is free; running OD when not necessary is expensive.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
