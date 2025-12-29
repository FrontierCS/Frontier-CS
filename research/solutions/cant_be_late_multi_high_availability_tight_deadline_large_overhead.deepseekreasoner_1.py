import json
from argparse import Namespace
import math
from typing import List, Tuple
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
        
        # Initialize strategy parameters
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.region_spot_history = []
        self.region_switches = 0
        self.consecutive_spot_failures = 0
        self.last_region = -1
        self.spot_attempts = 0
        self.spot_successes = 0
        self.min_slack_threshold = 2.0  # hours
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        # Track region switches
        if current_region != self.last_region:
            self.region_switches += 1
            self.last_region = current_region
        
        # Update spot statistics
        self.spot_attempts += 1
        if last_cluster_type == ClusterType.SPOT and has_spot:
            self.spot_successes += 1
            self.consecutive_spot_failures = 0
        elif last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_spot_failures += 1
        
        # Calculate remaining time and work
        elapsed_hours = self.env.elapsed_seconds / 3600.0
        remaining_time = self.deadline / 3600.0 - elapsed_hours
        work_done = sum(self.task_done_time) / 3600.0
        work_needed = self.task_duration / 3600.0 - work_done
        restart_hours = self.restart_overhead / 3600.0
        
        # Critical time check - if we're running out of time, use on-demand
        if remaining_time - work_needed < self.min_slack_threshold:
            # Check if switching could help
            if self._should_switch_for_emergency(current_region, num_regions, has_spot):
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        # Calculate effective time needed including potential restarts
        effective_work_needed = work_needed + (restart_hours * 0.5)  # Conservative estimate
        
        # If we have plenty of time, try to use spot
        if remaining_time > effective_work_needed * 1.5:  # Good slack
            if has_spot and self.consecutive_spot_failures < 3:
                # Try spot but with occasional checks
                if self.spot_attempts > 10 and self.spot_successes / self.spot_attempts < 0.7:
                    # Switch region if spot success rate is low
                    if self._find_better_region(current_region, num_regions):
                        return ClusterType.SPOT
                return ClusterType.SPOT
            elif not has_spot:
                # Try to find a region with spot
                if self._find_better_region(current_region, num_regions):
                    return ClusterType.SPOT
        
        # Moderate time pressure - mixed strategy
        if remaining_time > effective_work_needed * 1.2:
            # Use spot if available and we haven't had too many recent failures
            if has_spot and self.consecutive_spot_failures < 2:
                return ClusterType.SPOT
            # Otherwise use on-demand
            return ClusterType.ON_DEMAND
        
        # Time is tight - prefer on-demand
        return ClusterType.ON_DEMAND
    
    def _find_better_region(self, current_region: int, num_regions: int) -> bool:
        """Try to switch to a different region."""
        if num_regions <= 1:
            return False
        
        # Simple round-robin switching
        next_region = (current_region + 1) % num_regions
        if next_region != current_region:
            self.env.switch_region(next_region)
            return True
        return False
    
    def _should_switch_for_emergency(self, current_region: int, num_regions: int, has_spot: bool) -> bool:
        """Emergency switching when time is critical."""
        if not has_spot and num_regions > 1:
            # Try one switch in emergency
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            return True
        return False