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
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.price_ratio = self.ondemand_price / self.spot_price
        self.overhead_penalty = self.restart_overhead[0] * self.spot_price
        
        # Region tracking
        self.region_stats = {}
        self.current_region = 0
        self.last_region_change = 0
        self.region_switch_delay = 0
        
        # Safety margin for deadline
        self.safety_margin = 0.1  # 10% safety margin
        
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Get current state
        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        # Initialize region stats if needed
        if current_region not in self.region_stats:
            self.region_stats[current_region] = {
                'spot_available': 0,
                'steps_observed': 0,
                'last_spot_check': -1
            }
        
        # Update region stats
        stats = self.region_stats[current_region]
        stats['steps_observed'] += 1
        stats['last_spot_check'] = elapsed
        
        # Calculate progress and time constraints
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done
        time_left = self.deadline - elapsed
        
        # Critical check: if we cannot finish even with on-demand, use on-demand
        min_time_needed = work_left + (self.restart_overhead[0] if work_done > 0 else 0)
        if time_left < min_time_needed:
            return ClusterType.ON_DEMAND
        
        # Calculate conservative time needed with safety margin
        conservative_time_needed = work_left * 1.1 + self.restart_overhead[0]
        
        # If we're running out of time, use on-demand
        if time_left < conservative_time_needed:
            return ClusterType.ON_DEMAND
        
        # Check if we should consider switching regions
        should_switch = False
        if has_spot:
            stats['spot_available'] += 1
            spot_availability = stats['spot_available'] / stats['steps_observed']
            
            # Only switch if spot availability is low and we have time
            if (spot_availability < 0.5 and 
                time_left > work_left * 2 and 
                elapsed - self.last_region_change > gap * 2):
                
                # Find best region
                best_region = current_region
                best_availability = spot_availability
                
                for region in range(self.env.get_num_regions()):
                    if region == current_region:
                        continue
                        
                    if region in self.region_stats:
                        reg_stats = self.region_stats[region]
                        if reg_stats['steps_observed'] > 0:
                            reg_avail = reg_stats['spot_available'] / reg_stats['steps_observed']
                            if reg_avail > best_availability:
                                best_availability = reg_avail
                                best_region = region
                    else:
                        # Unknown region, might be worth exploring
                        if best_availability < 0.3:
                            best_region = region
                            break
                
                if best_region != current_region:
                    should_switch = True
        
        # Handle region switching
        if should_switch:
            self.env.switch_region(best_region)
            self.current_region = best_region
            self.last_region_change = elapsed
            
            # After switching, use spot if available in new region
            # We don't know availability yet, so be conservative
            if time_left > work_left * 1.5:
                return ClusterType.NONE  # Wait one step to assess new region
            else:
                return ClusterType.ON_DEMAND
        
        # Main decision logic
        if has_spot:
            # Use spot if we have time buffer
            time_buffer = time_left - work_left
            if time_buffer > self.restart_overhead[0] * 3:
                return ClusterType.SPOT
            elif time_buffer > self.restart_overhead[0]:
                # Use spot with lower probability as buffer decreases
                risk_factor = time_buffer / (self.restart_overhead[0] * 3)
                if elapsed % gap < gap * risk_factor:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND
        else:
            # No spot available
            if time_left < work_left * 1.2:
                # Running out of time, use on-demand
                return ClusterType.ON_DEMAND
            else:
                # Wait for spot if we have time
                wait_probability = min(0.7, (time_left - work_left) / (gap * 10))
                if elapsed % gap < gap * wait_probability:
                    return ClusterType.NONE
                else:
                    return ClusterType.ON_DEMAND
