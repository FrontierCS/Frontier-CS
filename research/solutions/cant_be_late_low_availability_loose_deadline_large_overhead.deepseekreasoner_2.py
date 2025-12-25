import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.last_spot_available = None
        self.consecutive_spot_unavailable = 0
        self.spot_availability_history = []
        self.spot_ratio_threshold = 0.3
        self.panic_mode = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_time = self.env.elapsed_seconds
        deadline = self.deadline
        restart_overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Calculate remaining work and time
        total_work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - total_work_done
        time_remaining = deadline - current_time
        
        # Update spot availability tracking
        self.spot_availability_history.append(has_spot)
        if len(self.spot_availability_history) > 100:
            self.spot_availability_history.pop(0)
        
        # Calculate spot availability ratio
        if len(self.spot_availability_history) > 0:
            spot_available_count = sum(self.spot_availability_history)
            spot_ratio = spot_available_count / len(self.spot_availability_history)
        else:
            spot_ratio = 0
        
        # Track consecutive unavailability for panic mode
        if has_spot:
            self.consecutive_spot_unavailable = 0
        else:
            self.consecutive_spot_unavailable += 1
        
        # Check if we need to enter panic mode (running out of time)
        time_per_work_unit = gap  # assuming 1 work unit per gap when running
        est_time_needed = remaining_work * time_per_work_unit
        time_buffer = time_remaining - est_time_needed
        
        # Enter panic mode if time is running out or spot is consistently unavailable
        if (time_buffer < restart_overhead * 2 or 
            self.consecutive_spot_unavailable > 5 or
            (time_buffer < restart_overhead * 4 and spot_ratio < self.spot_ratio_threshold)):
            self.panic_mode = True
        
        # Exit panic mode if we have good buffer and spot is available
        if (time_buffer > restart_overhead * 6 and 
            has_spot and 
            self.consecutive_spot_unavailable == 0):
            self.panic_mode = False
        
        # If in panic mode, use on-demand to ensure completion
        if self.panic_mode:
            if time_remaining <= 0:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND
        
        # Normal decision making
        if has_spot:
            # Use spot if available and we have time buffer
            if time_buffer > restart_overhead * 3:
                return ClusterType.SPOT
            else:
                # If buffer is low, be conservative with on-demand
                return ClusterType.ON_DEMAND
        else:
            # No spot available
            if time_buffer < restart_overhead:
                # If we're really tight on time, use on-demand
                return ClusterType.ON_DEMAND
            else:
                # Otherwise wait for spot to save cost
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)