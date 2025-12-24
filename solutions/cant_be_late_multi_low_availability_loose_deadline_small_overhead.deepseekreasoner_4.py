import json
from argparse import Namespace
from enum import Enum
import math
from typing import List, Dict, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

    def __init__(self, args):
        super().__init__(args)
        self.region_history = []
        self.spot_availability = {}
        self.region_costs = {}
        self.time_step = 0
        self.last_region = -1
        self.consecutive_spot_failures = 0
        self.spot_success_rate = {}
        self.region_switches = 0
        self.work_done_by_region = {}
        self.emergency_mode = False
        self.emergency_trigger_time = 0

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
        self.region_history = []
        self.spot_availability = {}
        self.region_costs = {}
        self.time_step = 0
        self.last_region = -1
        self.consecutive_spot_failures = 0
        self.spot_success_rate = {}
        self.region_switches = 0
        self.work_done_by_region = {}
        self.emergency_mode = False
        self.emergency_trigger_time = self.deadline * 0.7  # Enter emergency at 70% of deadline
        
        return self

    def _update_spot_stats(self, region_idx: int, has_spot: bool):
        """Update spot availability statistics for a region."""
        if region_idx not in self.spot_availability:
            self.spot_availability[region_idx] = []
            self.spot_success_rate[region_idx] = 0.0
            self.work_done_by_region[region_idx] = 0.0
        
        self.spot_availability[region_idx].append(1 if has_spot else 0)
        
        # Keep only recent history (last 50 steps)
        if len(self.spot_availability[region_idx]) > 50:
            self.spot_availability[region_idx].pop(0)
        
        # Update success rate
        if len(self.spot_availability[region_idx]) > 0:
            self.spot_success_rate[region_idx] = sum(self.spot_availability[region_idx]) / len(self.spot_availability[region_idx])

    def _get_best_spot_region(self, current_region: int) -> int:
        """Find the region with best spot availability."""
        num_regions = self.env.get_num_regions()
        
        # If we have no data for some regions, initialize them
        for i in range(num_regions):
            if i not in self.spot_success_rate:
                self.spot_success_rate[i] = 0.0
        
        # Find region with highest spot success rate
        best_region = current_region
        best_rate = self.spot_success_rate[current_region]
        
        for i in range(num_regions):
            if i != current_region:
                rate = self.spot_success_rate[i]
                if rate > best_rate + 0.1:  # Only switch if significantly better
                    best_region = i
                    best_rate = rate
        
        return best_region

    def _calculate_time_pressure(self) -> float:
        """Calculate how much time pressure we're under."""
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        if time_remaining <= 0 or work_remaining <= 0:
            return 0.0
        
        # Time needed if we use on-demand (no interruptions)
        time_needed_on_demand = work_remaining
        
        # Add safety margin for overheads
        safety_margin = self.restart_overhead * 3
        
        # Calculate pressure: 0 = no pressure, 1 = critical
        if time_needed_on_demand + safety_margin >= time_remaining:
            return 1.0
        
        pressure = 1.0 - (time_remaining - time_needed_on_demand - safety_margin) / (self.deadline * 0.3)
        return max(0.0, min(1.0, pressure))

    def _should_switch_to_ondemand(self, time_pressure: float, has_spot: bool) -> bool:
        """Decide whether to switch to on-demand."""
        # Emergency mode override
        if self.emergency_mode:
            return True
        
        # Critical time pressure
        if time_pressure > 0.8:
            return True
        
        # Too many consecutive spot failures
        if self.consecutive_spot_failures >= 3 and time_pressure > 0.3:
            return True
        
        # Low spot availability and moderate time pressure
        current_region = self.env.get_current_region()
        spot_rate = self.spot_success_rate.get(current_region, 0.0)
        if spot_rate < 0.3 and time_pressure > 0.4:
            return True
        
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        self.time_step += 1
        current_region = self.env.get_current_region()
        
        # Update statistics
        self._update_spot_stats(current_region, has_spot)
        
        # Track region switches
        if current_region != self.last_region:
            self.region_switches += 1
            self.last_region = current_region
        
        # Calculate work done in current region
        if self.task_done_time:
            self.work_done_by_region[current_region] = self.work_done_by_region.get(current_region, 0.0) + self.task_done_time[-1]
        
        # Check if we need emergency mode
        time_pressure = self._calculate_time_pressure()
        if time_pressure > 0.7 and not self.emergency_mode:
            self.emergency_mode = True
        
        # Update consecutive spot failures counter
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_spot_failures += 1
        else:
            self.consecutive_spot_failures = 0
        
        # If we're very close to deadline and still have work, use on-demand
        time_remaining = self.deadline - self.env.elapsed_seconds
        work_remaining = self.task_duration - sum(self.task_done_time)
        
        if time_remaining <= work_remaining + self.restart_overhead * 2:
            return ClusterType.ON_DEMAND
        
        # Check if we should switch to on-demand
        if self._should_switch_to_ondemand(time_pressure, has_spot):
            return ClusterType.ON_DEMAND
        
        # Try to find better region if spot is not available here
        if not has_spot and time_pressure < 0.6:
            best_region = self._get_best_spot_region(current_region)
            if best_region != current_region and self.region_switches < 10:  # Limit total switches
                self.env.switch_region(best_region)
                # After switching, we need to see if spot is available in the new region
                # We'll return NONE this step to avoid paying for potentially unavailable spot
                return ClusterType.NONE
        
        # If spot is available, use it (with some probability based on time pressure)
        if has_spot:
            # Be more conservative with spot as time pressure increases
            spot_probability = 1.0 - time_pressure * 0.5
            if self.time_step % 2 == 0 or spot_probability > 0.5:  # Use spot 50% of time or if probability is high
                return ClusterType.SPOT
        
        # Default to on-demand if spot strategy seems risky
        if time_pressure > 0.4:
            return ClusterType.ON_DEMAND
        
        # Otherwise, pause to wait for better conditions
        return ClusterType.NONE
