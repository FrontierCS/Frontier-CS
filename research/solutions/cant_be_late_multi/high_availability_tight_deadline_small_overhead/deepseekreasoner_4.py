import json
from argparse import Namespace
from typing import List
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "adaptive_scheduler"

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
        
        self.region_stats = []
        self.current_region_switch_time = 0
        self.last_action = ClusterType.NONE
        self.consecutive_failures = 0
        self.spot_success_count = 0
        self.region_history = []
        self.time_step = self.env.gap_seconds if hasattr(self.env, 'gap_seconds') else 3600.0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work and time
        total_done = sum(self.task_done_time)
        remaining_work = self.task_duration - total_done
        time_left = self.deadline - self.env.elapsed_seconds
        
        # If work is done, return NONE
        if remaining_work <= 0:
            return ClusterType.NONE
            
        # Calculate minimum time needed with current overhead
        current_overhead = self.remaining_restart_overhead
        effective_time_needed = remaining_work + current_overhead
        
        # Emergency mode: if we're running out of time, use on-demand
        buffer_factor = 1.5
        if time_left < effective_time_needed * buffer_factor:
            # If we need to switch to on-demand and it's a different type, accept overhead
            if last_cluster_type != ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        # Calculate safe threshold for using spot
        # More conservative as we approach deadline
        urgency = 1.0 - (time_left / (self.deadline - self.task_duration)) if time_left > 0 else 1.0
        urgency = max(0.0, min(1.0, urgency))
        
        # Dynamic region switching logic
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        # Try to use spot if available and conditions are favorable
        if has_spot:
            # Calculate probability threshold based on urgency
            # More likely to use spot when we have more time
            spot_probability = 0.8 - urgency * 0.3
            
            # Increase spot usage if we've had recent successes
            if self.spot_success_count > 2:
                spot_probability += 0.1
                
            # Use spot with calculated probability, but always if very safe
            time_safety_margin = time_left / effective_time_needed if effective_time_needed > 0 else float('inf')
            if time_safety_margin > 2.0 or self.spot_success_count > 1:
                self.spot_success_count += 1
                return ClusterType.SPOT
            elif time_safety_margin > 1.2 and self.consecutive_failures == 0:
                self.spot_success_count += 1
                return ClusterType.SPOT
            else:
                # Fall back to on-demand with some probability
                use_spot = (self.spot_success_count % 3 != 0)  # Simple pattern
                if use_spot:
                    self.spot_success_count += 1
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
        else:
            # Spot not available in current region
            self.spot_success_count = 0
            self.consecutive_failures += 1
            
            # Consider switching regions if we've had multiple failures
            if self.consecutive_failures >= 2 and num_regions > 1:
                # Simple round-robin region switching
                next_region = (current_region + 1) % num_regions
                self.env.switch_region(next_region)
                self.consecutive_failures = 0
                # After switching, use on-demand to be safe
                return ClusterType.ON_DEMAND
            
            # Use on-demand in current region
            return ClusterType.ON_DEMAND
    
    def _update_stats(self, region_idx: int, success: bool):
        """Update statistics for a region"""
        if len(self.region_stats) <= region_idx:
            self.region_stats.append({"attempts": 0, "successes": 0, "last_attempt": 0})
        
        stats = self.region_stats[region_idx]
        stats["attempts"] += 1
        stats["last_attempt"] = self.env.elapsed_seconds
        if success:
            stats["successes"] += 1
    
    def _get_best_region(self) -> int:
        """Get the region with best historical spot availability"""
        if not self.region_stats:
            return 0
        
        best_region = 0
        best_score = -1
        
        for i, stats in enumerate(self.region_stats):
            if stats["attempts"] > 0:
                success_rate = stats["successes"] / stats["attempts"]
                # Add recency bonus
                time_since_last = self.env.elapsed_seconds - stats["last_attempt"]
                recency_bonus = 1.0 / (1.0 + time_since_last / 3600.0)  # Decay over hours
                score = success_rate + recency_bonus * 0.1
                
                if score > best_score:
                    best_score = score
                    best_region = i
        
        return best_region