from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "AdaptiveDeadlineAwareStrategy"

    def __init__(self, args=None):
        super().__init__()
        self.args = args

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Current state
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        task_duration = self.task_duration
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Calculate progress
        completed_work = sum(self.task_done_time)
        remaining_work = task_duration - completed_work
        
        if remaining_work <= 0:
            return ClusterType.NONE
            
        time_left = deadline - elapsed
        
        # Safety padding (30 minutes) to account for quantization and minor overheads
        padding = 1800 
        
        # Calculate time strictly needed on OD to finish
        needed_if_od = remaining_work
        if last_cluster_type != ClusterType.ON_DEMAND:
            # If not currently on OD, we must pay restart overhead to switch/start
            needed_if_od += overhead
            
        # Panic Threshold calculation
        # If time_left is below this, we must use OD to guarantee deadline met
        # We add gap because our decision persists for at least one time step
        panic_threshold = needed_if_od + padding + gap
        
        if time_left < panic_threshold:
            return ClusterType.ON_DEMAND
            
        # If we are safe (above panic threshold)
        if has_spot:
            # Hysteresis logic:
            # If currently on OD, only switch to SPOT if we have extra buffer.
            # Switching OD->SPOT costs 'overhead'. If SPOT fails immediately, 
            # switching SPOT->OD costs 'overhead' again.
            if last_cluster_type == ClusterType.ON_DEMAND:
                switch_threshold = remaining_work + (2 * overhead) + padding + gap
                if time_left > switch_threshold:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            
            return ClusterType.SPOT
            
        # If Spot is unavailable but we have slack, wait (NONE) to save cost.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
