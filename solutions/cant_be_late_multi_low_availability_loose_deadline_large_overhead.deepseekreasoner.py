import json
from argparse import Namespace
from typing import List, Tuple
import heapq
import math

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

        # Store configuration
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.spot_available_history = []
        self.region_switches = 0
        self.last_decision = None
        self.consecutive_failures = 0
        self.region_stability = {}
        self.spot_probabilities = {}

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Get current state
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds

        # Calculate remaining work and time
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        remaining_time = self.deadline - elapsed

        # If task is done or no time left
        if remaining_work <= 0 or remaining_time <= 0:
            return ClusterType.NONE

        # If we have pending restart overhead, wait
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE

        # Calculate critical threshold
        work_hours_needed = remaining_work / 3600.0
        time_hours_left = remaining_time / 3600.0

        # If we're running out of time, use on-demand
        safety_margin = 2.0  # hours
        if time_hours_left - work_hours_needed < safety_margin:
            # Check if we can finish with on-demand
            if work_hours_needed <= time_hours_left:
                return ClusterType.ON_DEMAND
            else:
                # Not enough time even with on-demand, try spot as last resort
                if has_spot:
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND

        # Normal operation - use dynamic strategy
        # Update spot availability history for current region
        if len(self.spot_available_history) <= current_region:
            self.spot_available_history.append([])
        self.spot_available_history[current_region].append(has_spot)

        # Calculate spot reliability for each region
        reliabilities = []
        for region in range(num_regions):
            if region == current_region:
                hist = self.spot_available_history[region][-10:] if len(self.spot_available_history) > region else []
                if hist:
                    reliability = sum(hist) / len(hist)
                else:
                    reliability = 1.0 if has_spot else 0.0
            else:
                # For other regions, use optimistic estimate
                reliability = 0.7  # base reliability assumption

            # Adjust reliability based on remaining time
            time_factor = min(1.0, time_hours_left / 24.0)
            adjusted_reliability = reliability * time_factor

            # Calculate expected cost per hour
            expected_hourly_cost = (adjusted_reliability * self.spot_price +
                                    (1 - adjusted_reliability) * self.ondemand_price)

            # Add restart overhead cost
            restart_cost_hour = (self.restart_overhead / 3600.0) * self.ondemand_price
            expected_total_cost = expected_hourly_cost * work_hours_needed + restart_cost_hour

            reliabilities.append((expected_total_cost, adjusted_reliability, region))

        # Find best region based on expected cost
        reliabilities.sort()
        best_region_cost, best_reliability, best_region = reliabilities[0]

        # Decision logic
        if best_region != current_region:
            # Consider switching if significantly better
            current_cost = next(cost for cost, rel, reg in reliabilities if reg == current_region)
            if best_region_cost < current_cost * 0.8:  # 20% better
                self.env.switch_region(best_region)
                # After switching, check spot availability in new region
                # We'll use the has_spot for the new region in next iteration
                return ClusterType.NONE

        # In current/best region, decide spot vs on-demand
        if has_spot:
            # Use spot if reliable enough or we have time buffer
            time_buffer = time_hours_left - work_hours_needed
            if best_reliability > 0.6 or time_buffer > 4.0:
                return ClusterType.SPOT
            else:
                # Use on-demand if spot is unreliable and time is tight
                return ClusterType.ON_DEMAND
        else:
            # No spot available
            if work_hours_needed <= time_hours_left - 2.0:  # Can wait a bit
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND

    def _estimate_region_reliability(self, region_idx: int) -> float:
        """Estimate spot reliability for a region based on history."""
        if region_idx < len(self.spot_available_history):
            hist = self.spot_available_history[region_idx]
            if hist:
                # Weight recent history more heavily
                recent_len = min(5, len(hist))
                recent = hist[-recent_len:]
                if recent:
                    return sum(recent) / len(recent)
        return 0.5  # Default reliability
