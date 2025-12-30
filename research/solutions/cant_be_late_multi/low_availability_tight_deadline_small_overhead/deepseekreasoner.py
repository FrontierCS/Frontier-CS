import json
from argparse import Namespace
import math
from typing import List, Tuple
from collections import defaultdict

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "adaptive_threshold"

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
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.step_seconds = 3600.0  # 1 hour steps
        
        # Track region statistics
        self.region_stats = {}
        self.current_region = 0
        self.consecutive_spot_failures = 0
        self.max_consecutive_failures = 3
        
        # Time buffer for deadline
        self.safety_buffer = 3600.0  # 1 hour buffer
        
        # Performance tracking
        self.work_done = 0.0
        self.total_spot_attempts = 0
        self.spot_successes = 0
        
        return self

    def _compute_urgency(self) -> float:
        """Compute how urgent it is to finish the task."""
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done
        time_left = self.deadline - self.env.elapsed_seconds - self.safety_buffer
        
        if time_left <= 0:
            return float('inf')
        
        # Minimum steps needed if using on-demand (no interruptions)
        min_steps_needed = math.ceil(work_left / self.step_seconds)
        min_time_needed = min_steps_needed * self.step_seconds
        
        # Add potential overhead if we switch
        if self.env.cluster_type != ClusterType.ON_DEMAND:
            min_time_needed += self.restart_overhead
        
        # Urgency = ratio of minimum needed time to available time
        # Higher values mean more urgent
        if min_time_needed >= time_left:
            return float('inf')
        
        return min_time_needed / time_left

    def _find_best_region(self) -> int:
        """Find the region with best historical spot availability."""
        current = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        # If no stats yet, return current or next
        if not self.region_stats:
            return current
        
        # Find region with highest success rate
        best_region = current
        best_score = -1.0
        
        for region in range(num_regions):
            if region in self.region_stats:
                stats = self.region_stats[region]
                attempts = stats.get('attempts', 0)
                successes = stats.get('successes', 0)
                
                if attempts > 0:
                    success_rate = successes / attempts
                    # Prefer regions with higher success rate and more data
                    score = success_rate * min(1.0, attempts / 10.0)
                    if score > best_score:
                        best_score = score
                        best_region = region
            else:
                # Never tried this region - might be worth exploring
                if best_score < 0.5:  # Only explore if current options are poor
                    return region
        
        return best_region

    def _should_switch_region(self, has_spot: bool) -> bool:
        """Determine if we should switch regions."""
        current = self.env.get_current_region()
        
        # Don't switch if we're in the middle of overhead
        if self.remaining_restart_overhead > 0:
            return False
        
        # Don't switch too often
        if self.consecutive_spot_failures < self.max_consecutive_failures:
            return False
        
        # Find a better region
        best_region = self._find_best_region()
        if best_region != current:
            # Only switch if the best region is significantly better
            if current in self.region_stats and best_region in self.region_stats:
                current_stats = self.region_stats[current]
                best_stats = self.region_stats[best_region]
                
                current_rate = (current_stats.get('successes', 0) / 
                              max(1, current_stats.get('attempts', 1)))
                best_rate = (best_stats.get('successes', 0) / 
                           max(1, best_stats.get('attempts', 1)))
                
                if best_rate > current_rate + 0.2:  # 20% better
                    return True
            else:
                # Try a new region if we haven't tried the best one
                return True
        
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update work progress
        work_done = sum(self.task_done_time)
        self.work_done = work_done
        
        # Update current region
        self.current_region = self.env.get_current_region()
        
        # Update region statistics
        if last_cluster_type == ClusterType.SPOT:
            if self.current_region not in self.region_stats:
                self.region_stats[self.current_region] = {'attempts': 0, 'successes': 0}
            
            self.region_stats[self.current_region]['attempts'] += 1
            self.total_spot_attempts += 1
            
            # Check if last spot attempt was successful (we got work done)
            if self.task_done_time and self.task_done_time[-1] > 0:
                self.region_stats[self.current_region]['successes'] += 1
                self.spot_successes += 1
                self.consecutive_spot_failures = 0
            else:
                self.consecutive_spot_failures += 1
        
        # Reset failure count if we used on-demand
        if last_cluster_type == ClusterType.ON_DEMAND:
            self.consecutive_spot_failures = 0
        
        # Check if task is complete
        if work_done >= self.task_duration:
            return ClusterType.NONE
        
        # Check if we're past deadline
        if self.env.elapsed_seconds >= self.deadline:
            return ClusterType.NONE
        
        # Compute urgency
        urgency = self._compute_urgency()
        
        # If extremely urgent, use on-demand
        if urgency > 1.5 or work_done < self.task_duration * 0.1:
            # Early or late stage: be more conservative
            if not has_spot:
                return ClusterType.ON_DEMAND
        
        # Check if we should switch region
        if self._should_switch_region(has_spot):
            best_region = self._find_best_region()
            if best_region != self.current_region:
                self.env.switch_region(best_region)
                # After switching, we need to restart, so use NONE for this step
                return ClusterType.NONE
        
        # Main decision logic
        work_left = self.task_duration - work_done
        time_left = self.deadline - self.env.elapsed_seconds
        
        # Calculate safe threshold for using spot
        # Based on how much time we have vs how much work is left
        min_safe_time = work_left + self.restart_overhead * 2
        
        if time_left < min_safe_time:
            # Running out of time, use on-demand
            return ClusterType.ON_DEMAND
        
        if has_spot:
            # Use spot if available and we're not in critical phase
            if urgency < 0.8:  # Not too urgent
                return ClusterType.SPOT
            else:
                # Mix of spot and on-demand based on success rate
                if self.total_spot_attempts > 0:
                    spot_success_rate = self.spot_successes / self.total_spot_attempts
                    if spot_success_rate > 0.7:  # Good success rate
                        return ClusterType.SPOT
                    else:
                        return ClusterType.ON_DEMAND
                else:
                    return ClusterType.SPOT  # Try spot first
        
        # No spot available
        if time_left < work_left * 1.5:
            # Getting tight on time, use on-demand
            return ClusterType.ON_DEMAND
        
        # We have time, wait for spot or pause
        return ClusterType.NONE