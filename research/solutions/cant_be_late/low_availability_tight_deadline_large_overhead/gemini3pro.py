from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        work_completed = sum(self.task_done_time)
        work_remaining = max(0.0, self.task_duration - work_completed)
        
        # If work is effectively done, stop
        if work_remaining <= 1e-6:
            return ClusterType.NONE
            
        time_remaining = self.deadline - elapsed
        overhead = self.restart_overhead
        
        # Calculate time needed to finish on OD
        # If we are currently on OD, we don't pay overhead to continue.
        # If we are on SPOT or NONE, we must pay overhead to start OD.
        if last_cluster_type == ClusterType.ON_DEMAND:
            time_needed_od = work_remaining
        else:
            time_needed_od = work_remaining + overhead
            
        # Safety buffer: 2 timesteps to be safe against discretization/latency
        buffer = gap * 2.0
        
        # 1. Panic Check: If we are close to the "Point of No Return", force OD.
        # This ensures we meet the deadline regardless of Spot availability.
        if time_remaining <= time_needed_od + buffer:
            return ClusterType.ON_DEMAND
            
        # 2. If we have slack, try to optimize cost
        if has_spot:
            # Spot is available.
            
            # If we are currently on OD, switching to Spot saves money but consumes slack (overhead).
            # We should only switch if we have significant slack to justify the risk/cost of switching.
            if last_cluster_type == ClusterType.ON_DEMAND:
                slack = time_remaining - work_remaining
                # Threshold: Need enough slack to pay overhead plus a substantial margin
                # to prevent flapping between OD and Spot.
                if slack > (overhead * 3.0 + buffer):
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            
            # If not on OD (NONE or SPOT), simply use Spot.
            return ClusterType.SPOT
        
        else:
            # Spot is unavailable, and we are not in Panic Mode.
            
            # If we are currently on OD, stick with it to avoid paying overheads repeatedly.
            # Stopping OD now would save money, but we'd likely have to restart it later (paying overhead again).
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
                
            # Otherwise, wait for Spot (save money).
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)