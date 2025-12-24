from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "cant_be_late_robust"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize strategy.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide the cluster type for the next time step.
        """
        # Retrieve environment state
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        deadline = self.deadline
        overhead = self.restart_overhead
        
        # Calculate remaining work
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # If work is finished, do nothing
        if work_remaining <= 0:
            return ClusterType.NONE
            
        # Calculate time remaining until deadline
        time_remaining = deadline - elapsed
        
        # Determine strict safety threshold.
        # We must finish the task before the deadline. 
        # The most reliable way is On-Demand (OD).
        # We calculate the latest possible moment we must be on OD to guarantee completion.
        # We account for:
        # 1. Remaining work duration
        # 2. Restart overhead (in case we need to switch/boot OD)
        # 3. Safety buffer (multiple of gap) to handle discrete time steps and margin of error
        
        # If we skip OD this step (return SPOT or NONE), we consume 'gap' seconds.
        # We must ensure that at (elapsed + gap), we still have enough time to finish using OD.
        # Required time on OD = work_remaining + restart_overhead
        # We add a buffer of 3 * gap for robustness.
        
        safety_buffer = 3.0 * gap
        required_time_on_od = work_remaining + overhead + safety_buffer
        
        # Check if we are approaching the point of no return
        # If remaining time at the NEXT step is too close to required time, force OD now.
        if (time_remaining - gap) < required_time_on_od:
            return ClusterType.ON_DEMAND
            
        # If we are safely within the deadline slack:
        # Prioritize cost savings.
        if has_spot:
            # Spot is available and we have time to risk preemption/overheads
            return ClusterType.SPOT
        else:
            # Spot is unavailable, but we have plenty of slack.
            # Pause (NONE) to save money rather than burning expensive OD budget needlessly.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
