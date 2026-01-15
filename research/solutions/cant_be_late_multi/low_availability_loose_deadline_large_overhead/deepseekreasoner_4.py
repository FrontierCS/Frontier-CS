import json
from argparse import Namespace
import math
from typing import List, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""
    
    NAME = "adaptive_safety_first"
    
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
        
        # Pre-calculate constants for efficiency
        self.overhead_seconds = float(config["overhead"]) * 3600
        self.task_duration_seconds = float(config["duration"]) * 3600
        self.deadline_seconds = float(config["deadline"]) * 3600
        
        # Initialize state
        self.regions_availability = {}
        self.current_region = 0
        self.consecutive_failures = 0
        self.last_spot_availability = True
        self.safety_threshold = 0.7  # Start being conservative
        
        return self
    
    def _update_availability_stats(self, region_idx: int, has_spot: bool) -> None:
        """Track spot availability patterns per region."""
        if region_idx not in self.regions_availability:
            self.regions_availability[region_idx] = {
                'total_steps': 0,
                'spot_available_steps': 0,
                'last_available': has_spot
            }
        
        stats = self.regions_availability[region_idx]
        stats['total_steps'] += 1
        if has_spot:
            stats['spot_available_steps'] += 1
        stats['last_available'] = has_spot
    
    def _get_best_region(self, current_region: int, has_spot: bool) -> int:
        """Find the best region to switch to based on availability history."""
        num_regions = self.env.get_num_regions()
        best_region = current_region
        best_score = -1
        
        for region in range(num_regions):
            if region == current_region:
                # Prefer staying if current region has spot
                if has_spot:
                    return current_region
                continue
            
            if region in self.regions_availability:
                stats = self.regions_availability[region]
                if stats['total_steps'] > 0:
                    availability_rate = stats['spot_available_steps'] / stats['total_steps']
                    # Prefer regions with recent spot availability
                    recency_bonus = 1.0 if stats['last_available'] else 0.0
                    score = availability_rate * 0.7 + recency_bonus * 0.3
                    
                    if score > best_score:
                        best_score = score
                        best_region = region
        
        # If no good alternative found, try next region
        if best_score <= 0:
            best_region = (current_region + 1) % num_regions
        
        return best_region
    
    def _calculate_time_pressure(self) -> float:
        """Calculate how much time pressure we're under (0-1 scale)."""
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline_seconds - elapsed
        completed_work = sum(self.task_done_time)
        remaining_work = self.task_duration_seconds - completed_work
        
        if remaining_time <= 0 or remaining_work <= 0:
            return 1.0
        
        # Account for potential overheads
        conservative_remaining = remaining_work + self.overhead_seconds * 2
        time_ratio = conservative_remaining / remaining_time
        
        # Normalize to 0-1 range (1 means high pressure)
        pressure = min(max(time_ratio, 0.0), 1.0)
        return pressure
    
    def _should_use_ondemand(self, time_pressure: float, has_spot: bool) -> bool:
        """Determine if we should use on-demand based on time pressure and spot reliability."""
        if not has_spot:
            return True
        
        # Increase on-demand usage as time pressure increases
        if time_pressure > 0.8:
            return True
        elif time_pressure > 0.6 and self.consecutive_failures > 2:
            return True
        elif time_pressure > 0.4 and self.consecutive_failures > 4:
            return True
        
        return False
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update current region
        self.current_region = self.env.get_current_region()
        
        # Update availability statistics
        self._update_availability_stats(self.current_region, has_spot)
        
        # Update consecutive failures count
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = max(0, self.consecutive_failures - 1)
        
        # Calculate time pressure
        time_pressure = self._calculate_time_pressure()
        
        # Adjust safety threshold based on time pressure
        self.safety_threshold = 0.3 + time_pressure * 0.5
        
        # If we have pending restart overhead, we need to wait
        if self.remaining_restart_overhead > 0:
            # Consider switching region if current one doesn't have spot
            if not has_spot and time_pressure < 0.8:
                best_region = self._get_best_region(self.current_region, has_spot)
                if best_region != self.current_region:
                    self.env.switch_region(best_region)
            return ClusterType.NONE
        
        # Check if we should switch regions
        if not has_spot and time_pressure < 0.7:
            best_region = self._get_best_region(self.current_region, has_spot)
            if best_region != self.current_region:
                self.env.switch_region(best_region)
                # Switching incurs overhead, so wait
                return ClusterType.NONE
        
        # Calculate remaining work and time
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline_seconds - elapsed
        completed_work = sum(self.task_done_time)
        remaining_work = self.task_duration_seconds - completed_work
        
        # If no work left, do nothing
        if remaining_work <= 0:
            return ClusterType.NONE
        
        # If out of time, try anything
        if remaining_time <= 0:
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        # Estimate time if we use spot vs on-demand
        time_per_step = self.env.gap_seconds
        effective_work_per_spot_step = time_per_step - (self.overhead_seconds if last_cluster_type != ClusterType.SPOT else 0)
        effective_work_per_ondemand_step = time_per_step - (self.overhead_seconds if last_cluster_type != ClusterType.ON_DEMAND else 0)
        
        # Calculate minimum steps needed
        min_spot_steps = math.ceil(remaining_work / max(effective_work_per_spot_step, 1))
        min_ondemand_steps = math.ceil(remaining_work / max(effective_work_per_ondemand_step, 1))
        
        # Calculate available time steps
        available_steps = remaining_time / time_per_step
        
        # Decision logic
        if min_ondemand_steps > available_steps:
            # Can't finish even with on-demand
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        elif min_spot_steps > available_steps * self.safety_threshold:
            # Running out of time, use on-demand
            return ClusterType.ON_DEMAND
        else:
            # We have time, use spot if available
            if has_spot:
                return ClusterType.SPOT
            elif time_pressure < 0.6:
                # Try switching region instead of using expensive on-demand
                best_region = self._get_best_region(self.current_region, has_spot)
                if best_region != self.current_region:
                    self.env.switch_region(best_region)
                    return ClusterType.NONE
                else:
                    return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND