import json
from argparse import Namespace
from typing import List, Tuple, Dict
import heapq
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with cost optimization."""
    
    NAME = "optimized_spot_scheduler"
    
    def solve(self, spec_path: str) -> "Solution":
        """Initialize the solution from spec_path config."""
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
        self.on_demand_price = 3.06  # $/hr
        self.price_ratio = self.spot_price / self.on_demand_price
        
        # Time conversion
        self.hours_to_seconds = 3600.0
        
        # State tracking
        self.current_region = 0
        self.last_decision = ClusterType.NONE
        self.consecutive_spot_failures = 0
        self.max_spot_failures = 3
        self.switch_count = 0
        self.max_switches = 10
        
        # Performance tracking
        self.progress_history = []
        self.time_elapsed_history = []
        
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        
        Strategy overview:
        1. Check if we're close to deadline -> use on-demand
        2. Check if spot is available and we haven't had too many failures -> use spot
        3. If no spot and we have time -> try another region
        4. If no spot in any region or time running out -> use on-demand
        5. If cost would be too high with on-demand -> pause and wait for spot
        """
        
        # Get current state
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        task_duration = self.task_duration
        restart_overhead = self.restart_overhead
        
        # Calculate progress and time remaining
        total_done = sum(self.task_done_time)
        progress = total_done / task_duration if task_duration > 0 else 0
        remaining_work = task_duration - total_done
        time_remaining = deadline - elapsed
        
        # Store progress for trend analysis
        self.progress_history.append(progress)
        self.time_elapsed_history.append(elapsed)
        if len(self.progress_history) > 100:
            self.progress_history.pop(0)
            self.time_elapsed_history.pop(0)
        
        # Calculate required progress rate
        if time_remaining > 0 and remaining_work > 0:
            required_rate = remaining_work / time_remaining
        else:
            required_rate = float('inf')
        
        # Calculate effective time considering restart overhead
        effective_time_remaining = time_remaining
        if self.remaining_restart_overhead > 0:
            effective_time_remaining -= self.remaining_restart_overhead
        
        # Calculate slack ratio (how much extra time we have)
        if remaining_work > 0:
            slack_ratio = effective_time_remaining / remaining_work
        else:
            slack_ratio = float('inf')
        
        # Critical condition: must use on-demand to finish on time
        critical_time = False
        if effective_time_remaining <= remaining_work * 1.1:  # 10% buffer
            critical_time = True
        
        # Calculate cost efficiency threshold
        # We're willing to use spot if probability of success is high enough
        # Based on price ratio and slack
        if slack_ratio > 2.0:  # Plenty of time
            spot_confidence_threshold = 0.3
        elif slack_ratio > 1.5:
            spot_confidence_threshold = 0.5
        elif slack_ratio > 1.2:
            spot_confidence_threshold = 0.7
        else:
            spot_confidence_threshold = 0.9
        
        # Check if we should switch regions
        should_switch = False
        if not has_spot and not critical_time:
            # Only switch if we have time and haven't switched too much
            if self.switch_count < self.max_switches:
                # Calculate if switching might help
                time_per_switch = restart_overhead
                estimated_switch_cost = time_per_switch / self.hours_to_seconds
                
                if (effective_time_remaining - estimated_switch_cost) > remaining_work * 1.05:
                    # Try to find a better region
                    best_region = current_region
                    for i in range(num_regions):
                        if i != current_region:
                            # Simple heuristic: try alternating regions
                            if (elapsed // self.hours_to_seconds) % num_regions == i:
                                best_region = i
                                break
                    
                    if best_region != current_region:
                        self.env.switch_region(best_region)
                        self.current_region = best_region
                        self.switch_count += 1
                        # After switching, we need to restart
                        return ClusterType.NONE
        
        # Decision logic
        if critical_time:
            # Must use on-demand to guarantee completion
            if last_cluster_type != ClusterType.ON_DEMAND:
                self.consecutive_spot_failures = 0
            return ClusterType.ON_DEMAND
        
        elif has_spot and slack_ratio > 1.1:
            # Use spot if available and we have reasonable slack
            if self.consecutive_spot_failures < self.max_spot_failures:
                # Check if we're making good progress
                if len(self.progress_history) >= 5:
                    recent_progress = self.progress_history[-1] - self.progress_history[-5]
                    recent_time = self.time_elapsed_history[-1] - self.time_elapsed_history[-5]
                    if recent_time > 0:
                        actual_rate = recent_progress * task_duration / recent_time
                        if actual_rate < required_rate * 0.8:
                            # Progress too slow, consider on-demand
                            return ClusterType.ON_DEMAND
                
                self.consecutive_spot_failures = 0
                return ClusterType.SPOT
            else:
                # Too many consecutive spot failures, try on-demand temporarily
                return ClusterType.ON_DEMAND
        
        elif not has_spot and slack_ratio > 1.3:
            # No spot available but we have time
            # Check if we should wait or use on-demand
            wait_efficiency = (slack_ratio - 1.0) / self.price_ratio
            
            if wait_efficiency > 2.0:  # Worth waiting
                self.consecutive_spot_failures += 1
                return ClusterType.NONE
            else:
                # Not worth waiting, use on-demand
                if last_cluster_type != ClusterType.ON_DEMAND:
                    self.consecutive_spot_failures = 0
                return ClusterType.ON_DEMAND
        
        elif not has_spot:
            # No spot and limited time
            # Use on-demand to make progress
            if last_cluster_type != ClusterType.ON_DEMAND:
                self.consecutive_spot_failures = 0
            return ClusterType.ON_DEMAND
        
        else:  # has_spot but limited slack
            # Balance between spot and on-demand based on risk
            risk_tolerance = min(1.0, (slack_ratio - 1.0) / 0.5)
            
            if risk_tolerance > spot_confidence_threshold:
                self.consecutive_spot_failures = 0
                return ClusterType.SPOT
            else:
                if last_cluster_type != ClusterType.ON_DEMAND:
                    self.consecutive_spot_failures = 0
                return ClusterType.ON_DEMAND