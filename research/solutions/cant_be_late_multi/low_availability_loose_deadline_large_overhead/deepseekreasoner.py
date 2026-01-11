import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

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
        
        # Initialize strategy state
        self.region_data = []
        self.current_region = 0
        self.last_action = ClusterType.NONE
        self.consecutive_failures = 0
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.budget_ratio = 0.5
        self.aggressive_threshold = 0.7
        self.patience = 2
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Get current state
        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done
        time_left = deadline - elapsed
        
        # If work is done, just return NONE
        if work_left <= 0:
            return ClusterType.NONE
        
        # Calculate time pressure
        time_pressure = 1.0 - (time_left / deadline) if deadline > 0 else 0
        
        # Calculate minimum time needed if using only on-demand
        min_time_needed = work_left + self.restart_overhead
        
        # If we can't finish even with perfect on-demand, switch to on-demand
        if time_left < min_time_needed:
            # Check if we need to switch region first
            if self.remaining_restart_overhead > 0:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND
        
        # Calculate conservative threshold
        # As deadline approaches, become more aggressive with on-demand
        safety_margin = max(1.5, 3.0 * (1.0 - time_pressure))
        required_rate = work_left / max(time_left - safety_margin * self.restart_overhead, 0.1)
        
        # Normalize required rate (max is 1.0 per gap_seconds)
        max_rate = 1.0 / self.env.gap_seconds
        normalized_required = required_rate / max_rate
        
        # Decide action based on conditions
        action = ClusterType.NONE
        
        # If we have high time pressure or low progress, use on-demand
        if (time_pressure > self.aggressive_threshold or 
            normalized_required > 0.8 or 
            work_left > time_left * 0.7):
            
            if self.remaining_restart_overhead > 0:
                action = ClusterType.NONE
            else:
                action = ClusterType.ON_DEMAND
                
        # Otherwise, try to use spot if available
        elif has_spot:
            # Check if we should switch regions for better spot availability
            if self.consecutive_failures >= self.patience:
                num_regions = self.env.get_num_regions()
                next_region = (current_region + 1) % num_regions
                if next_region != current_region:
                    self.env.switch_region(next_region)
                    self.consecutive_failures = 0
                    return ClusterType.NONE
            
            if self.remaining_restart_overhead > 0:
                action = ClusterType.NONE
            else:
                action = ClusterType.SPOT
                
        # If spot not available but we have time, wait
        elif time_left > min_time_needed * 1.5:
            action = ClusterType.NONE
            
        # Otherwise, use on-demand
        else:
            if self.remaining_restart_overhead > 0:
                action = ClusterType.NONE
            else:
                action = ClusterType.ON_DEMAND
        
        # Update consecutive failures counter
        if action == ClusterType.SPOT and not has_spot:
            self.consecutive_failures += 1
        elif action == ClusterType.SPOT and has_spot:
            self.consecutive_failures = max(0, self.consecutive_failures - 1)
        
        self.last_action = action
        return action