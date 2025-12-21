import json
from argparse import Namespace
from typing import List
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""
    
    NAME = "my_strategy"

    def __init__(self, args):
        super().__init__(args)
        self.gap_seconds = None
        self.remaining_work_history = []
        self.spot_availability_history = {}
        self.region_switch_history = []
        self.last_action = None
        self.consecutive_spot_failures = 0
        self.spot_attempt_count = 0
        self.spot_success_count = 0
        self.current_region_spot_reliability = 1.0

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
        
        # Initialize data structures
        self.remaining_work_history = []
        self.spot_availability_history = {}
        self.region_switch_history = []
        self.last_action = None
        self.consecutive_spot_failures = 0
        self.spot_attempt_count = 0
        self.spot_success_count = 0
        self.current_region_spot_reliability = 1.0
        
        return self

    def _calculate_remaining_work(self) -> float:
        """Calculate remaining work in seconds."""
        work_done = sum(self.task_done_time)
        remaining = self.task_duration - work_done
        return max(0.0, remaining)

    def _calculate_remaining_time(self) -> float:
        """Calculate remaining time until deadline in seconds."""
        return self.deadline - self.env.elapsed_seconds

    def _get_time_pressure(self) -> float:
        """Calculate time pressure ratio (0-1)."""
        remaining_work = self._calculate_remaining_work()
        remaining_time = self._calculate_remaining_time()
        
        if remaining_time <= 0 or remaining_work <= 0:
            return 1.0
        
        # Account for potential restart overhead
        safe_time = remaining_time - self.restart_overhead
        if safe_time <= 0:
            return 1.0
            
        required_rate = remaining_work / safe_time
        return min(1.0, required_rate * 1.2)  # Add 20% safety margin

    def _update_spot_reliability(self, region_idx: int, has_spot: bool):
        """Update spot reliability statistics for current region."""
        if region_idx not in self.spot_availability_history:
            self.spot_availability_history[region_idx] = {
                'attempts': 0,
                'successes': 0,
                'recent_successes': 0,
                'recent_attempts': 0
            }
        
        stats = self.spot_availability_history[region_idx]
        stats['attempts'] += 1
        stats['recent_attempts'] = min(10, stats['recent_attempts'] + 1)
        
        if has_spot:
            stats['successes'] += 1
            stats['recent_successes'] = min(10, stats['recent_successes'] + 1)
        
        # Calculate reliability (weight recent history more)
        recent_reliability = (stats['recent_successes'] / stats['recent_attempts']) if stats['recent_attempts'] > 0 else 1.0
        overall_reliability = (stats['successes'] / stats['attempts']) if stats['attempts'] > 0 else 1.0
        self.current_region_spot_reliability = 0.7 * recent_reliability + 0.3 * overall_reliability

    def _find_best_region(self, current_region: int, has_spot_current: bool) -> int:
        """Find the best region to switch to based on historical reliability."""
        num_regions = self.env.get_num_regions()
        
        # If we have no history for other regions, stay or explore
        if not self.spot_availability_history:
            # If current region has spot, stay
            if has_spot_current:
                return current_region
            # Otherwise try another region
            return (current_region + 1) % num_regions
        
        best_region = current_region
        best_reliability = self.current_region_spot_reliability if current_region in self.spot_availability_history else 0
        
        for region in range(num_regions):
            if region == current_region:
                continue
                
            if region in self.spot_availability_history:
                stats = self.spot_availability_history[region]
                attempts = stats['attempts']
                successes = stats['successes']
                recent_successes = stats['recent_successes']
                recent_attempts = stats['recent_attempts']
                
                if recent_attempts > 0:
                    recent_reliability = recent_successes / recent_attempts
                    overall_reliability = successes / attempts if attempts > 0 else 0
                    reliability = 0.7 * recent_reliability + 0.3 * overall_reliability
                    
                    if reliability > best_reliability:
                        best_reliability = reliability
                        best_region = region
        
        return best_region

    def _should_switch_region(self, current_region: int, has_spot: bool) -> bool:
        """Determine if we should switch regions."""
        # Don't switch if we're in restart overhead
        if self.remaining_restart_overhead > 0:
            return False
            
        # Don't switch too frequently
        if len(self.region_switch_history) >= 3:
            recent_switches = self.region_switch_history[-3:]
            if sum(recent_switches) >= 2:  # Switched too much recently
                return False
        
        # If current region has spot and good reliability, stay
        if has_spot and self.current_region_spot_reliability > 0.7:
            return False
            
        # Check if there's a better region
        best_region = self._find_best_region(current_region, has_spot)
        return best_region != current_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Initialize gap_seconds on first call
        if self.gap_seconds is None:
            self.gap_seconds = 3600.0  # Default to 1 hour if not available
        
        # Update spot reliability for current region
        current_region = self.env.get_current_region()
        self._update_spot_reliability(current_region, has_spot)
        
        # Calculate critical metrics
        remaining_work = self._calculate_remaining_work()
        remaining_time = self._calculate_remaining_time()
        time_pressure = self._get_time_pressure()
        
        # Check if we're done
        if remaining_work <= 0:
            return ClusterType.NONE
            
        # Check if we'll miss deadline even with on-demand
        min_time_needed = remaining_work + self.restart_overhead
        if remaining_time < min_time_needed:
            # Emergency mode - use on-demand to try to finish
            return ClusterType.ON_DEMAND
        
        # Decide whether to switch region
        if self._should_switch_region(current_region, has_spot):
            best_region = self._find_best_region(current_region, has_spot)
            if best_region != current_region:
                self.env.switch_region(best_region)
                self.region_switch_history.append(1)
                if len(self.region_switch_history) > 10:
                    self.region_switch_history.pop(0)
                # After switching, we need to restart, so return NONE for this step
                return ClusterType.NONE
        
        # Update region switch history for staying
        self.region_switch_history.append(0)
        if len(self.region_switch_history) > 10:
            self.region_switch_history.pop(0)
        
        # Strategy decision based on time pressure and spot availability
        if time_pressure > 0.8:
            # High time pressure - prefer on-demand
            return ClusterType.ON_DEMAND
        elif time_pressure > 0.5:
            # Medium time pressure - mixed strategy
            if has_spot and self.current_region_spot_reliability > 0.6:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        else:
            # Low time pressure - prefer spot or pause
            if remaining_time > remaining_work * 1.5:  # We have plenty of time
                if has_spot and self.current_region_spot_reliability > 0.4:
                    return ClusterType.SPOT
                else:
                    # Wait for better spot availability
                    return ClusterType.NONE
            else:
                if has_spot:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
