import json
from argparse import Namespace
import heapq
from collections import defaultdict, deque
from typing import List, Tuple, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""
    
    NAME = "adaptive_multi_region"

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
        
        # Initialize internal state
        self.region_stats = None
        self.spot_history = defaultdict(list)
        self.region_switches = 0
        self.consecutive_spots = 0
        self.last_decision = ClusterType.NONE
        self.spot_availability_buffer = deque(maxlen=5)
        self.safety_margin = 1.2  # 20% safety margin
        self.aggressiveness = 0.7  # How aggressively we use spot
        
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Get current state
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        elapsed = self.env.elapsed_seconds
        remaining_work = self.task_duration - sum(self.task_done_time)
        time_left = self.deadline - elapsed
        
        # Record spot availability
        self.spot_availability_buffer.append(has_spot)
        spot_reliability = sum(self.spot_availability_buffer) / len(self.spot_availability_buffer)
        
        # Calculate critical thresholds
        total_work_needed = remaining_work
        if self.remaining_restart_overhead > 0:
            total_work_needed += self.remaining_restart_overhead
        
        # Calculate time efficiency needed
        time_efficiency_needed = total_work_needed / max(time_left, 0.001)
        
        # If we're in critical zone, use on-demand
        if time_efficiency_needed > 0.9 or time_left < total_work_needed * 1.5:
            # We need to be conservative
            if has_spot and spot_reliability > 0.8 and self.last_decision == ClusterType.SPOT:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        # Calculate cost-benefit for spot usage
        spot_cost_saving = 3.06 - 0.9701  # $/hour
        risk_factor = max(0, 1.0 - (time_left / self.deadline))
        
        # Dynamic aggressiveness based on progress
        progress_ratio = sum(self.task_done_time) / self.task_duration
        dynamic_aggressiveness = self.aggressiveness * (1.0 - progress_ratio * 0.3)
        
        # Determine if we should consider switching regions
        should_consider_switch = (
            len(self.spot_availability_buffer) >= 3 and
            spot_reliability < 0.5 and
            num_regions > 1 and
            self.region_switches < 5  # Limit region switches
        )
        
        if should_consider_switch:
            # Try to find a better region
            best_region = current_region
            best_estimated_reliability = spot_reliability
            
            # Simple region exploration (in practice would use more sophisticated logic)
            # For now, just cycle through regions
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            self.region_switches += 1
            # Reset spot history for new region
            self.spot_availability_buffer.clear()
        
        # Decision logic
        if not has_spot:
            # No spot available, use on-demand if we need to make progress
            if time_efficiency_needed > 0.6 or self.last_decision == ClusterType.ON_DEMAND:
                self.last_decision = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND
            else:
                # Pause briefly to wait for spot
                self.last_decision = ClusterType.NONE
                return ClusterType.NONE
        
        # We have spot available
        if self.last_decision == ClusterType.SPOT:
            # Continue with spot if we've had success recently
            self.consecutive_spots += 1
            if self.consecutive_spots >= 2:  # If we've had 2+ successful spot runs
                self.last_decision = ClusterType.SPOT
                return ClusterType.SPOT
        
        # Decide between spot and on-demand
        spot_probability = min(spot_reliability * (1.0 + self.consecutive_spots * 0.1), 1.0)
        expected_spot_value = spot_probability * spot_cost_saving - (1 - spot_probability) * self.restart_overhead * 3.06 / 3600
        
        if expected_spot_value > 0.5 * dynamic_aggressiveness:
            self.last_decision = ClusterType.SPOT
            self.consecutive_spots = 1
            return ClusterType.SPOT
        else:
            self.last_decision = ClusterType.ON_DEMAND
            self.consecutive_spots = 0
            return ClusterType.ON_DEMAND