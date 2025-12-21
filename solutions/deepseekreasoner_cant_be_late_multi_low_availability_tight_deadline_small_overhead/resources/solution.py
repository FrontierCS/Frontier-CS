import json
from argparse import Namespace
from typing import List
import heapq

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"

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
        self.od_price = 3.06  # $/hour
        self.spot_price = 0.9701  # $/hour
        self.gap_hours = self.env.gap_seconds / 3600.0
        
        # Convert to hours for easier calculations
        self.task_duration_hours = self.task_duration / 3600.0
        self.deadline_hours = self.deadline / 3600.0
        self.restart_overhead_hours = self.restart_overhead / 3600.0
        
        # State tracking
        self.region_switches = 0
        self.consecutive_spot_failures = 0
        self.last_action = ClusterType.NONE
        self.last_region = -1
        self.work_done_hours = 0.0
        self.spot_history = {}
        self.region_availability = {}
        self.region_costs = {}
        
        return self

    def _update_state(self, last_cluster_type: ClusterType, has_spot: bool):
        """Update internal state tracking."""
        current_region = self.env.get_current_region()
        
        # Track region availability
        if current_region not in self.region_availability:
            self.region_availability[current_region] = []
        self.region_availability[current_region].append(1 if has_spot else 0)
        
        # Keep only recent history (last 50 steps)
        if len(self.region_availability[current_region]) > 50:
            self.region_availability[current_region].pop(0)
            
        # Track work done
        if self.task_done_time:
            self.work_done_hours = sum(self.task_done_time) / 3600.0
        
        # Track region switches
        if current_region != self.last_region:
            self.region_switches += 1
            self.last_region = current_region
            
        self.last_action = last_cluster_type

    def _get_time_pressure(self) -> float:
        """Calculate time pressure factor (0-1)."""
        time_elapsed_hours = self.env.elapsed_seconds / 3600.0
        time_remaining_hours = self.deadline_hours - time_elapsed_hours
        work_remaining_hours = self.task_duration_hours - self.work_done_hours
        
        if time_remaining_hours <= 0 or work_remaining_hours <= 0:
            return 1.0
            
        # Normalize time pressure
        required_rate = work_remaining_hours / max(time_remaining_hours, 0.001)
        max_possible_rate = 1.0 / self.gap_hours  # Work rate if running continuously
        pressure = min(1.0, required_rate / max_possible_rate * 1.2)
        
        return pressure

    def _get_best_region(self, has_spot: bool) -> int:
        """Find best region to switch to based on history."""
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        # If current region has spot and we're not under high pressure, stay
        if has_spot and self._get_time_pressure() < 0.8:
            return current_region
            
        # Calculate region scores
        region_scores = []
        for region in range(num_regions):
            if region == current_region:
                score = 0
            else:
                score = -1  # Penalty for switching
                
            # Add availability bonus
            if region in self.region_availability:
                history = self.region_availability[region]
                if history:
                    availability = sum(history) / len(history)
                    score += availability * 2
                    
            region_scores.append((score, region))
            
        # Return best region
        region_scores.sort(reverse=True)
        return region_scores[0][1]

    def _should_use_ondemand(self, has_spot: bool, time_pressure: float) -> bool:
        """Determine if we should use on-demand."""
        # If no time pressure and spot is available, use spot
        if has_spot and time_pressure < 0.3:
            return False
            
        # High time pressure -> use on-demand
        if time_pressure > 0.7:
            return True
            
        # Medium time pressure and no spot -> use on-demand
        if not has_spot and time_pressure > 0.4:
            return True
            
        # If we've had consecutive spot failures, switch to on-demand
        if self.consecutive_spot_failures > 3 and time_pressure > 0.2:
            return True
            
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Update internal state
        self._update_state(last_cluster_type, has_spot)
        
        # Get current state
        current_region = self.env.get_current_region()
        time_pressure = self._get_time_pressure()
        
        # Check if we're in restart overhead
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
            
        # Find best region
        best_region = self._get_best_region(has_spot)
        
        # Switch region if beneficial
        if best_region != current_region:
            # Only switch if not under extreme time pressure or if current region has no spot
            if time_pressure < 0.9 or not has_spot:
                self.env.switch_region(best_region)
                # After switching, we need to wait for restart overhead
                return ClusterType.NONE
        
        # Update has_spot for new region if we switched
        if best_region != current_region:
            # We don't know spot availability in new region yet
            # Be conservative and use on-demand if under pressure
            if time_pressure > 0.6:
                self.consecutive_spot_failures = 0
                return ClusterType.ON_DEMAND
            else:
                # Wait to see spot availability in next step
                return ClusterType.NONE
        
        # Decide on cluster type
        if self._should_use_ondemand(has_spot, time_pressure):
            self.consecutive_spot_failures = 0
            return ClusterType.ON_DEMAND
        elif has_spot:
            # Use spot if available
            self.consecutive_spot_failures = 0
            return ClusterType.SPOT
        else:
            # No spot available, wait if we have time
            if time_pressure < 0.5:
                self.consecutive_spot_failures += 1
                return ClusterType.NONE
            else:
                # Under time pressure with no spot, use on-demand
                self.consecutive_spot_failures = 0
                return ClusterType.ON_DEMAND
