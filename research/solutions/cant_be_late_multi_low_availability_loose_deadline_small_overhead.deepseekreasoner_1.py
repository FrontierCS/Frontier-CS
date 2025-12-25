import json
from argparse import Namespace
import math
from enum import IntEnum
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class RegionState:
    def __init__(self):
        self.spot_available = True
        self.spot_history = []


class Solution(MultiRegionStrategy):
    NAME = "adaptive_spot_strategy"

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
        self.region_states = {}
        self.current_region_quality = {}
        self.region_switch_timer = 0
        self.consecutive_failures = 0
        self.last_decision = ClusterType.NONE
        self.emergency_mode = False
        self.spot_use_count = 0
        self.od_use_count = 0
        self.time_since_last_switch = 0
        
        return self

    def _calculate_remaining_time(self) -> float:
        """Calculate remaining time until deadline."""
        return self.deadline - self.env.elapsed_seconds

    def _calculate_progress(self) -> float:
        """Calculate progress percentage."""
        if self.task_duration == 0:
            return 1.0
        total_done = sum(self.task_done_time)
        return total_done / self.task_duration

    def _get_best_alternative_region(self, current_region: int) -> int:
        """Find the best alternative region to switch to."""
        num_regions = self.env.get_num_regions()
        best_region = current_region
        best_score = -1
        
        # Simple round-robin fallback
        for i in range(num_regions):
            if i != current_region:
                # Use simple heuristic: regions are indexed sequentially
                # In production, would use actual spot availability history
                return i
        
        return (current_region + 1) % num_regions

    def _should_switch_to_ondemand(self) -> bool:
        """Determine if we should switch to on-demand based on time pressure."""
        remaining_time = self._calculate_remaining_time()
        progress = self._calculate_progress()
        remaining_work = self.task_duration * (1 - progress)
        
        # Conservative estimate with overhead
        time_needed = remaining_work + self.restart_overhead
        
        # If we're running out of time, switch to on-demand
        safety_margin = max(self.restart_overhead * 3, 3600)  # 1 hour or 3x overhead
        
        if remaining_time < time_needed + safety_margin:
            return True
        
        # If we've had too many spot failures recently
        if self.consecutive_failures > 3:
            return True
            
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        remaining_time = self._calculate_remaining_time()
        progress = self._calculate_progress()
        
        # Update region quality tracking
        if current_region not in self.current_region_quality:
            self.current_region_quality[current_region] = 1.0
        
        # Update timer for region switching
        self.time_since_last_switch += 1
        
        # Emergency check: if we're critically behind schedule
        if progress < 0.5 and remaining_time < self.task_duration * (1 - progress) * 1.5:
            self.emergency_mode = True
        
        # If in emergency mode, use on-demand exclusively
        if self.emergency_mode:
            if last_cluster_type != ClusterType.ON_DEMAND and self.remaining_restart_overhead <= 0:
                self.consecutive_failures = 0
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND
        
        # Check if we should switch to on-demand due to time pressure
        if self._should_switch_to_ondemand():
            if last_cluster_type != ClusterType.ON_DEMAND and self.remaining_restart_overhead <= 0:
                self.consecutive_failures = 0
                return ClusterType.ON_DEMAND
        
        # Try to use spot if available
        if has_spot:
            # Occasionally switch regions to find better spot availability
            if self.time_since_last_switch > 10 and self.consecutive_failures > 0:
                num_regions = self.env.get_num_regions()
                if num_regions > 1:
                    new_region = self._get_best_alternative_region(current_region)
                    if new_region != current_region:
                        self.env.switch_region(new_region)
                        self.time_since_last_switch = 0
                        self.consecutive_failures = 0
                        # After switching, start with spot if available
                        return ClusterType.SPOT
            
            # Normal spot usage
            if last_cluster_type != ClusterType.SPOT and self.remaining_restart_overhead <= 0:
                self.consecutive_failures = 0
                self.spot_use_count += 1
                return ClusterType.SPOT
            elif last_cluster_type == ClusterType.SPOT:
                self.consecutive_failures = 0
                return ClusterType.SPOT
        
        # Spot not available or can't use it
        if not has_spot:
            self.consecutive_failures += 1
            
            # Try switching region if spot is not available for too long
            if self.consecutive_failures > 2 and self.time_since_last_switch > 5:
                num_regions = self.env.get_num_regions()
                if num_regions > 1:
                    new_region = self._get_best_alternative_region(current_region)
                    if new_region != current_region:
                        self.env.switch_region(new_region)
                        self.time_since_last_switch = 0
                        # Don't reset failures completely, but reduce
                        self.consecutive_failures = max(0, self.consecutive_failures - 1)
        
        # Fallback to on-demand if we can't use spot
        if last_cluster_type != ClusterType.ON_DEMAND and self.remaining_restart_overhead <= 0:
            self.od_use_count += 1
            return ClusterType.ON_DEMAND
        elif last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND
        
        # If all else fails, wait (but only if we have time)
        if remaining_time > self.task_duration * (1 - progress) * 2:
            return ClusterType.NONE
        else:
            # Time is tight, use on-demand
            if self.remaining_restart_overhead <= 0:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE
