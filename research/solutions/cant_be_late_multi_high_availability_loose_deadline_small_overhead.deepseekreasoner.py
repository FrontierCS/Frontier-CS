import json
from argparse import Namespace
from enum import IntEnum
import heapq
from typing import List, Tuple, Dict

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class NodeState(IntEnum):
    IDLE = 0
    SPOT_RUNNING = 1
    ON_DEMAND_RUNNING = 2
    OVERHEAD = 3


class RegionInfo:
    __slots__ = ('spot_availability', 'spot_history', 'recent_availability', 'score')
    
    def __init__(self):
        self.spot_availability = True
        self.spot_history = []
        self.recent_availability = 0
        self.score = 0.0


class Solution(MultiRegionStrategy):
    NAME = "optimized_spot_scheduler"

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
        self.step_seconds = 3600.0  # 1 hour per step
        self.safety_margin = 0.1  # 10% safety margin
        
        # State tracking
        self.regions_info = []
        self.spot_windows = []
        self.region_switch_penalty = 0
        self.last_action = ClusterType.NONE
        self.consecutive_spot_failures = 0
        self.spot_success_streak = 0
        self.critical_time = False
        
        # Performance history
        self.performance_history = []
        self.best_region = 0
        self.region_samples = 0
        
        return self

    def _initialize_regions(self, num_regions: int):
        """Initialize region tracking structures"""
        if not self.regions_info:
            self.regions_info = [RegionInfo() for _ in range(num_regions)]
            self.spot_windows = [[] for _ in range(num_regions)]

    def _update_spot_history(self, region_idx: int, available: bool):
        """Update spot availability history for a region"""
        info = self.regions_info[region_idx]
        info.spot_availability = available
        info.spot_history.append(available)
        
        # Keep recent history (last 10 steps)
        if len(info.spot_history) > 10:
            info.spot_history.pop(0)
        
        # Update recent availability score
        if len(info.spot_history) > 0:
            info.recent_availability = sum(info.spot_history) / len(info.spot_history)
            
        # Update region score (higher for regions with consistent spot)
        if available:
            info.score = info.score * 0.9 + 0.1
        else:
            info.score = info.score * 0.9

    def _calculate_time_pressure(self) -> float:
        """Calculate time pressure factor (0 to 1)"""
        if self.deadline <= self.env.elapsed_seconds:
            return 1.0
        
        total_work = self.task_duration
        work_done = sum(self.task_done_time)
        work_left = total_work - work_done
        
        time_left = self.deadline - self.env.elapsed_seconds
        time_needed = work_left + (self.restart_overhead if self.remaining_restart_overhead > 0 else 0)
        
        if time_left <= 0:
            return 1.0
        if time_needed <= 0:
            return 0.0
            
        pressure = max(0.0, min(1.0, (time_needed / time_left) * (1.0 + self.safety_margin)))
        return pressure

    def _should_switch_to_ondemand(self, time_pressure: float, has_spot: bool) -> bool:
        """Determine if we should switch to on-demand"""
        # Always use on-demand if we're in critical time
        if time_pressure > 0.95:
            return True
        
        # Use on-demand if spot is unreliable recently
        if self.consecutive_spot_failures >= 3:
            return True
            
        # Use on-demand if we don't have much time left for spot to stabilize
        if time_pressure > 0.7 and not has_spot:
            return True
            
        return False

    def _find_best_spot_region(self, current_region: int) -> int:
        """Find the best region for spot instances"""
        num_regions = self.env.get_num_regions()
        
        # If we haven't sampled enough, explore
        if self.region_samples < num_regions * 2:
            # Round-robin exploration
            next_region = (current_region + 1) % num_regions
            return next_region
        
        # Exploit: choose region with best score
        best_score = -1
        best_region = current_region
        
        for i in range(num_regions):
            score = self.regions_info[i].score
            if score > best_score:
                best_score = score
                best_region = i
                
        return best_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize regions if needed
        current_region = self.env.get_current_region()
        self._initialize_regions(self.env.get_num_regions())
        
        # Update spot history for current region
        self._update_spot_history(current_region, has_spot)
        self.region_samples += 1
        
        # Calculate time pressure
        time_pressure = self._calculate_time_pressure()
        self.critical_time = time_pressure > 0.8
        
        # Update failure/success streaks
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_spot_failures += 1
            self.spot_success_streak = 0
        elif last_cluster_type == ClusterType.SPOT and has_spot:
            self.consecutive_spot_failures = 0
            self.spot_success_streak += 1
        else:
            self.consecutive_spot_failures = 0
        
        # Check if we should switch to on-demand
        if self._should_switch_to_ondemand(time_pressure, has_spot):
            # If switching from spot to on-demand in same region
            if last_cluster_type == ClusterType.SPOT and has_spot:
                return ClusterType.ON_DEMAND
            # If we're already on on-demand, stay
            elif last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            # Otherwise switch to on-demand
            else:
                return ClusterType.ON_DEMAND
        
        # Try to use spot if available
        if has_spot:
            # Check if we should switch regions for better spot
            if (self.spot_success_streak < 2 and 
                time_pressure < 0.6 and 
                len(self.regions_info) > 1):
                
                best_region = self._find_best_spot_region(current_region)
                if best_region != current_region:
                    self.env.switch_region(best_region)
                    # After switching, we need to check spot availability in new region
                    # Since we don't know yet, be conservative and use on-demand for one step
                    return ClusterType.ON_DEMAND
            
            return ClusterType.SPOT
        
        # Spot not available - decide what to do
        if time_pressure < 0.4:
            # We have time, try to find spot in another region
            if len(self.regions_info) > 1:
                best_region = self._find_best_spot_region(current_region)
                if best_region != current_region:
                    self.env.switch_region(best_region)
                    # Conservative: use on-demand for one step after switch
                    return ClusterType.ON_DEMAND
            
            # No better region found or single region, wait
            return ClusterType.NONE
        else:
            # Some time pressure, use on-demand
            return ClusterType.ON_DEMAND