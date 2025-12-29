import json
from argparse import Namespace
import numpy as np
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""
    
    NAME = "my_strategy"
    
    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.
        """
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
        self.spot_price = 0.9701  # $/hr
        self.ondemand_price = 3.06  # $/hr
        self.gap_hours = self.env.gap_seconds / 3600.0
        self.required_hours = self.task_duration / 3600.0
        self.deadline_hours = self.deadline / 3600.0
        self.overhead_hours = self.restart_overhead / 3600.0
        
        # State tracking
        self.current_region = 0
        self.region_spot_history = {}
        self.last_action = ClusterType.NONE
        self.consecutive_failures = 0
        self.time_until_deadline_start = None
        
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Get current state
        elapsed_hours = self.env.elapsed_seconds / 3600.0
        if self.time_until_deadline_start is None:
            self.time_until_deadline_start = self.deadline_hours - elapsed_hours
        
        remaining_work = self.required_hours - sum(self.task_done_time) / 3600.0
        time_left = self.deadline_hours - elapsed_hours
        
        # If we're in restart overhead, do nothing
        if self.remaining_restart_overhead > 0:
            self.last_action = ClusterType.NONE
            return ClusterType.NONE
        
        # Emergency mode: if we're running out of time, use on-demand
        if time_left <= remaining_work * 1.2:
            # Need to guarantee completion
            if last_cluster_type != ClusterType.ON_DEMAND:
                self.consecutive_failures = 0
            self.last_action = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        # If spot is available and we haven't had too many consecutive failures
        if has_spot and self.consecutive_failures < 3:
            # Check if we should switch regions
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            
            # Track spot availability in current region
            if current_region not in self.region_spot_history:
                self.region_spot_history[current_region] = []
            self.region_spot_history[current_region].append(has_spot)
            
            # Keep recent history (last 10 steps)
            if len(self.region_spot_history[current_region]) > 10:
                self.region_spot_history[current_region].pop(0)
            
            # Calculate spot reliability in current region
            if len(self.region_spot_history[current_region]) >= 5:
                recent_history = self.region_spot_history[current_region][-5:]
                reliability = sum(recent_history) / len(recent_history)
                
                # If reliability is low, consider switching regions
                if reliability < 0.5 and num_regions > 1:
                    # Try to find a better region
                    best_region = current_region
                    best_reliability = reliability
                    
                    for region in range(num_regions):
                        if region == current_region:
                            continue
                        
                        if region in self.region_spot_history:
                            hist = self.region_spot_history[region]
                            if len(hist) >= 3:
                                region_reliability = sum(hist[-3:]) / len(hist[-3:])
                                if region_reliability > best_reliability:
                                    best_reliability = region_reliability
                                    best_region = region
                    
                    if best_region != current_region:
                        self.env.switch_region(best_region)
                        self.consecutive_failures = 0
                        self.last_action = ClusterType.SPOT
                        return ClusterType.SPOT
            
            # Use spot in current region
            self.consecutive_failures = 0
            self.last_action = ClusterType.SPOT
            return ClusterType.SPOT
        
        # Spot not available or too many failures
        elif has_spot:
            # Too many consecutive failures, use on-demand for safety
            self.last_action = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        else:
            # No spot available, check if we should wait or use on-demand
            # Calculate how much time we can afford to wait
            time_needed_if_start_now = remaining_work + (0 if last_cluster_type == ClusterType.ON_DEMAND else self.overhead_hours)
            
            if time_left > time_needed_if_start_now * 1.5:
                # We have buffer time, can wait for spot
                self.consecutive_failures += 1
                self.last_action = ClusterType.NONE
                return ClusterType.NONE
            else:
                # Not enough time to wait, use on-demand
                self.consecutive_failures = 0
                self.last_action = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND