import json
from argparse import Namespace
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType
from typing import List, Tuple
import math

class Solution(MultiRegionStrategy):
    NAME = "my_strategy"
    
    def __init__(self, args):
        super().__init__(args)
        self.initialized = False
        self.spot_history = []
        self.current_region = 0
        self.strategy_state = "spot_seeking"
        self.consecutive_spot_failures = 0
        self.last_action = ClusterType.NONE
        self.region_quality = {}
        self.time_since_switch = 0
        self.spot_availability_window = 5
        self.max_spot_wait = 3
        self.min_spot_confidence = 0.7
        self.required_work_rate = 1.0
        self.emergency_mode = False
    
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
        self.initialized = True
        
        # Calculate required work rate (work per second needed to finish by deadline)
        total_work_needed = self.task_duration[0] * 3600  # Convert to seconds
        total_time_available = self.deadline_hours[0] * 3600
        self.required_work_rate = total_work_needed / total_time_available
        
        # Initialize region quality tracking
        num_regions = self.env.get_num_regions()
        for i in range(num_regions):
            self.region_quality[i] = {
                'spot_availability': 0.5,  # Initial guess
                'recent_spot': [],
                'last_visit': -1
            }
        
        return self
    
    def _update_region_quality(self, region_idx: int, has_spot: bool):
        """Update our belief about spot availability in a region"""
        if region_idx not in self.region_quality:
            self.region_quality[region_idx] = {
                'spot_availability': 0.5,
                'recent_spot': [],
                'last_visit': self.env.elapsed_seconds
            }
        
        # Record this observation
        self.region_quality[region_idx]['recent_spot'].append(1 if has_spot else 0)
        
        # Keep only recent history
        if len(self.region_quality[region_idx]['recent_spot']) > self.spot_availability_window:
            self.region_quality[region_idx]['recent_spot'].pop(0)
        
        # Update availability estimate
        if self.region_quality[region_idx]['recent_spot']:
            recent_sum = sum(self.region_quality[region_idx]['recent_spot'])
            self.region_quality[region_idx]['spot_availability'] = (
                recent_sum / len(self.region_quality[region_idx]['recent_spot'])
            )
        
        self.region_quality[region_idx]['last_visit'] = self.env.elapsed_seconds
    
    def _get_best_alternative_region(self) -> int:
        """Find the best alternative region to switch to"""
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        best_region = current_region
        best_score = -1
        
        current_time = self.env.elapsed_seconds
        
        for region in range(num_regions):
            if region == current_region:
                continue
            
            quality = self.region_quality.get(region, {'spot_availability': 0.5, 'last_visit': -1})
            
            # Calculate score: higher spot availability, more recent visit gets higher score
            time_since_visit = current_time - quality['last_visit']
            recency_bonus = 1.0 / (1.0 + time_since_visit / 3600.0)  # Decay over hours
            
            score = quality['spot_availability'] * 0.7 + recency_bonus * 0.3
            
            if score > best_score:
                best_score = score
                best_region = region
        
        return best_region
    
    def _calculate_work_progress(self) -> Tuple[float, float, float]:
        """Calculate work done, remaining, and time remaining"""
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration[0] * 3600 - work_done
        time_remaining = self.deadline_hours[0] * 3600 - self.env.elapsed_seconds
        
        return work_done, work_remaining, time_remaining
    
    def _calculate_required_efficiency(self) -> float:
        """Calculate the minimum work efficiency needed to finish on time"""
        work_done, work_remaining, time_remaining = self._calculate_work_progress()
        
        if time_remaining <= 0 or work_remaining <= 0:
            return 0.0
        
        # Account for potential restart overheads
        safe_time_remaining = time_remaining - self.restart_overhead_hours[0] * 3600 * 2
        
        if safe_time_remaining <= 0:
            return float('inf')
        
        return work_remaining / safe_time_remaining
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self.initialized:
            return ClusterType.NONE
        
        current_region = self.env.get_current_region()
        
        # Update our knowledge of current region
        self._update_region_quality(current_region, has_spot)
        
        # Calculate progress metrics
        work_done, work_remaining, time_remaining = self._calculate_work_progress()
        required_efficiency = self._calculate_required_efficiency()
        
        # Emergency mode if we're running out of time
        time_ratio = time_remaining / (work_remaining + 1e-6)
        
        # Check if we need to go into emergency mode
        if time_ratio < 1.5 or required_efficiency > 1.2:
            self.emergency_mode = True
        
        # If task is done, do nothing
        if work_remaining <= 0:
            return ClusterType.NONE
        
        # If no time left, use on-demand as last resort
        if time_remaining <= 0:
            return ClusterType.ON_DEMAND
        
        # Emergency mode: use on-demand to ensure completion
        if self.emergency_mode:
            # Still try spot if it's available and we have some buffer
            if has_spot and time_ratio > 1.2:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        # Calculate if we should consider switching regions
        should_consider_switch = False
        
        # Consider switching if:
        # 1. We've had consecutive spot failures
        # 2. Current region has poor spot availability
        # 3. We haven't switched recently
        
        current_quality = self.region_quality[current_region]['spot_availability']
        
        if (self.consecutive_spot_failures >= self.max_spot_wait and 
            current_quality < self.min_spot_confidence and
            self.time_since_switch > 2):
            should_consider_switch = True
        
        # Check if we're falling behind schedule
        current_efficiency = work_done / (self.env.elapsed_seconds + 1e-6)
        if current_efficiency < self.required_work_rate * 0.8:
            should_consider_switch = True
        
        # Perform region switch if needed
        if should_consider_switch and self.env.get_num_regions() > 1:
            best_alt_region = self._get_best_alternative_region()
            if best_alt_region != current_region:
                self.env.switch_region(best_alt_region)
                self.consecutive_spot_failures = 0
                self.time_since_switch = 0
                # After switch, we need to wait for next step to know spot availability
                return ClusterType.NONE
        
        # Main decision logic
        if has_spot:
            # Use spot if available and we're not in a critical time crunch
            if time_ratio > 1.3 or required_efficiency < 1.0:
                self.consecutive_spot_failures = 0
                self.last_action = ClusterType.SPOT
                return ClusterType.SPOT
            else:
                # Time is tight, use on-demand to be safe
                self.last_action = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND
        else:
            # Spot not available
            self.consecutive_spot_failures += 1
            
            # Decide whether to wait or use on-demand
            if (time_ratio > 2.0 and 
                self.consecutive_spot_failures < self.max_spot_wait and
                current_quality > 0.3):
                # Wait for spot to become available
                self.last_action = ClusterType.NONE
                return ClusterType.NONE
            else:
                # Use on-demand
                self.consecutive_spot_failures = 0
                self.last_action = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND
        
        # Fallback (shouldn't reach here)
        return ClusterType.NONE