from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "lazy_deadline_solver"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate current progress and time budget
        # self.task_done_time contains durations of completed segments
        completed_work = sum(self.task_done_time)
        remaining_work = max(0.0, self.task_duration - completed_work)
        
        current_time = self.env.elapsed_seconds
        time_until_deadline = self.deadline - current_time
        
        # Safety margin calculations
        # overhead: Time lost when starting a new instance or switching
        overhead = self.restart_overhead
        # gap: The simulation step size. We need at least one gap buffer.
        gap = self.env.gap_seconds
        
        # Buffer: A safety margin to ensure we don't miss the deadline due to 
        # discrete time steps or overhead transitions. 
        # 30 minutes (1800s) is selected as a safe balance between cost and reliability
        # given the 22-hour slack in the problem setting.
        safety_buffer = 1800.0 + gap
        
        # Determine the "Must Run OD" threshold.
        # If the remaining time drops below (work needed + overhead + buffer),
        # we must switch to On-Demand to guarantee completion.
        # We include overhead in the check even if currently running to maintain a safe latch.
        time_needed_for_od_finish = remaining_work + overhead + safety_buffer
        
        # 1. Critical Mode: Deadline approaching
        if time_until_deadline <= time_needed_for_od_finish:
            return ClusterType.ON_DEMAND
            
        # 2. Economic Mode: Plenty of slack
        # If Spot is available, use it (cheapest option).
        if has_spot:
            return ClusterType.SPOT
            
        # 3. Waiting Mode: No Spot, but plenty of slack
        # Wait for Spot to become available rather than burning money on OD.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
