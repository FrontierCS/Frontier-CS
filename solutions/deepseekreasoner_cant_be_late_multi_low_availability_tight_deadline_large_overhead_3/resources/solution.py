import json
from argparse import Namespace
from typing import List, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"
    
    def __init__(self, args):
        super().__init__(args)
        self.region_history = []
        self.spot_unavailable_count = 0
        self.last_action = ClusterType.NONE
        self.work_segments = []
        self.consecutive_spot = 0
        self.time_until_deadline = 0
        
    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)
            
        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)
        
        # Initialize tracking variables
        self.region_history = []
        self.spot_unavailable_count = 0
        self.last_action = ClusterType.NONE
        self.work_segments = []
        self.consecutive_spot = 0
        self.time_until_deadline = 0
        
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        self.region_history.append(current_region)
        
        # Calculate remaining work and time
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        elapsed = self.env.elapsed_seconds
        self.time_until_deadline = self.deadline - elapsed
        
        # If we've completed the work, do nothing
        if remaining_work <= 0:
            return ClusterType.NONE
            
        # If we're out of time, use on-demand to try to finish
        if self.time_until_deadline <= 0:
            return ClusterType.ON_DEMAND
            
        # Calculate how many hours we can afford to wait
        remaining_hours = self.time_until_deadline / 3600.0
        required_hours = remaining_work / 3600.0
        
        # Always try to finish with on-demand if we're running out of time
        # This accounts for restart overheads and ensures we meet the deadline
        time_buffer = 2.0  # hours buffer for safety
        if required_hours >= remaining_hours - time_buffer:
            return ClusterType.ON_DEMAND
            
        # If spot is available and we have time buffer, use spot
        if has_spot and remaining_hours > required_hours + 2.0:
            # Check if we've had too many spot interruptions recently
            if self.consecutive_spot < 5:  # Limit consecutive spot usage
                self.consecutive_spot += 1
                self.spot_unavailable_count = 0
                return ClusterType.SPOT
        
        # If spot is not available, check other regions
        if not has_spot:
            self.spot_unavailable_count += 1
            self.consecutive_spot = 0
            
            # If we've had too many spot unavailability in this region, try another
            if self.spot_unavailable_count > 3:
                num_regions = self.env.get_num_regions()
                if num_regions > 1:
                    # Try next region in round-robin fashion
                    next_region = (current_region + 1) % num_regions
                    self.env.switch_region(next_region)
                    self.spot_unavailable_count = 0
        
        # Default to on-demand if we can't use spot
        return ClusterType.ON_DEMAND
