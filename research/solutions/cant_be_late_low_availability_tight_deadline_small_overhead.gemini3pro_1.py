from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Access environment and task parameters
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        deadline = self.deadline
        overhead = self.restart_overhead
        
        # Calculate progress
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # Check if task is complete
        if work_remaining <= 1e-6:
            return ClusterType.NONE

        time_remaining = deadline - elapsed
        
        # Safety buffer: ensure we have at least 2 steps of margin
        # before the absolute latest start time for On-Demand.
        safety_buffer = 2.0 * gap
        
        # Calculate the threshold time where we MUST be on On-Demand to guarantee completion.
        # Logic: To finish on OD, we need `work_remaining` time.
        # If we are not currently on OD (or if we switch), we incur `overhead`.
        # We use `work_remaining + overhead` as the threshold for all states to prevent flapping:
        # - If on Spot/None: We must switch to OD if time < work + overhead.
        # - If on OD: We should not switch to Spot if time < work + overhead, because if Spot 
        #   fails immediately, we would need to pay overhead to return to OD, which we can't afford.
        safe_threshold = work_remaining + overhead + safety_buffer
        
        # Panic Logic: If time is running out, use reliable On-Demand
        if time_remaining <= safe_threshold:
            return ClusterType.ON_DEMAND
            
        # Strategy Logic: If safe, minimize cost
        if has_spot:
            # Optimization: If currently on OD, avoid switching to Spot if remaining work 
            # is too small to justify the overhead cost/risk.
            # Heuristic: If work_remaining is very small compared to overhead, staying on OD is better.
            if last_cluster_type == ClusterType.ON_DEMAND and work_remaining < 0.5 * overhead:
                return ClusterType.ON_DEMAND
                
            return ClusterType.SPOT
        
        # If no Spot available and we have slack, wait (NONE) to save money
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)