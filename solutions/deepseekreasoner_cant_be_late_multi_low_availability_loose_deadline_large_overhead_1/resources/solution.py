import json
from argparse import Namespace
from enum import Enum
import heapq
from typing import List, Tuple, Optional
from collections import defaultdict

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Action(Enum):
    SPOT = 0
    ON_DEMAND = 1
    NONE = 2
    SWITCH_SPOT = 3
    SWITCH_ON_DEMAND = 4


class Solution(MultiRegionStrategy):
    NAME = "optimized_multi_region"

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
        
        # Pre-calculated constants
        self.spot_price = 0.9701
        self.on_demand_price = 3.06
        self.gap_hours = self.env.gap_seconds / 3600.0
        
        # State tracking
        self.region_spot_history = defaultdict(list)
        self.last_action = None
        self.consecutive_spot_failures = 0
        self.switch_cooldown = 0
        
        return self

    def _calculate_urgency(self) -> float:
        """Calculate urgency based on remaining time and work."""
        remaining_work = self.task_duration - sum(self.task_done_time)
        time_left = self.deadline - self.env.elapsed_seconds
        
        if remaining_work <= 0:
            return 0.0
        
        # How many hours of work we can afford with current time
        available_time_hours = time_left / 3600.0
        work_needed_hours = remaining_work / 3600.0
        
        # Urgency from 0 to 1, where 1 means critical
        urgency = 1.0 - (available_time_hours / (work_needed_hours * 2.0))
        return max(0.0, min(1.0, urgency))

    def _estimate_region_spot_availability(self, region_idx: int) -> float:
        """Estimate spot availability probability for a region."""
        if region_idx not in self.region_spot_history:
            return 0.5  # Default unknown
        
        history = self.region_spot_history[region_idx]
        if not history:
            return 0.5
        
        # Weight recent history more
        recent_len = min(10, len(history))
        recent = history[-recent_len:]
        return sum(recent) / len(recent)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update spot history for current region
        current_region = self.env.get_current_region()
        self.region_spot_history[current_region].append(1 if has_spot else 0)
        
        # Keep history limited
        if len(self.region_spot_history[current_region]) > 50:
            self.region_spot_history[current_region].pop(0)
        
        # Calculate urgency
        urgency = self._calculate_urgency()
        
        # If we have pending restart overhead, we can't do useful work
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        # Check if we're done
        if sum(self.task_done_time) >= self.task_duration:
            return ClusterType.NONE
        
        # If we're in switch cooldown, stay in current region
        if self.switch_cooldown > 0:
            self.switch_cooldown -= 1
        else:
            # Consider switching to better region
            best_region = current_region
            best_score = -1.0
            
            for region in range(self.env.get_num_regions()):
                if region == current_region:
                    continue
                
                # Estimate spot availability
                spot_prob = self._estimate_region_spot_availability(region)
                
                # Score based on spot probability and urgency
                score = spot_prob * 0.7 + (1 - urgency) * 0.3
                
                if score > best_score:
                    best_score = score
                    best_region = region
            
            # Switch if significantly better and not in high urgency
            if (best_region != current_region and best_score > 0.6 and 
                urgency < 0.7 and self.switch_cooldown == 0):
                self.env.switch_region(best_region)
                self.switch_cooldown = 3  # Prevent frequent switching
                return ClusterType.NONE
        
        # Decision logic based on urgency and spot availability
        remaining_work = self.task_duration - sum(self.task_done_time)
        time_left = self.deadline - self.env.elapsed_seconds
        
        # Critical: use on-demand if we're running out of time
        work_time_needed = remaining_work + (self.restart_overhead if last_cluster_type == ClusterType.SPOT else 0)
        if time_left < work_time_needed * 1.2:  # 20% safety margin
            return ClusterType.ON_DEMAND
        
        # High urgency: prefer on-demand
        if urgency > 0.7:
            return ClusterType.ON_DEMAND
        
        # Medium urgency: mix of spot and on-demand
        if urgency > 0.4:
            if has_spot:
                # Use spot but with caution
                if self.consecutive_spot_failures < 2:
                    return ClusterType.SPOT
                else:
                    # Too many recent failures, use on-demand
                    return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND
        
        # Low urgency: prefer spot
        if has_spot:
            self.consecutive_spot_failures = 0
            return ClusterType.SPOT
        else:
            self.consecutive_spot_failures += 1
            
            # If spot unavailable and not urgent, wait
            if urgency < 0.3:
                return ClusterType.NONE
            else:
                # Try another region
                next_region = (current_region + 1) % self.env.get_num_regions()
                if next_region != current_region and self.switch_cooldown == 0:
                    self.env.switch_region(next_region)
                    self.switch_cooldown = 2
                return ClusterType.NONE
