import json
import collections
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "heuristic_scheduler"  # REQUIRED: unique identifier

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

        # Custom initialization for the strategy
        self.num_regions = self.env.get_num_regions()
        
        # --- Hyperparameters for the strategy ---
        
        # Use a sliding window to estimate recent spot availability.
        self.history_window_size = 8
        
        # Required improvement in spot rate to justify a switch.
        self.rate_improvement_threshold = 0.1
        
        # Critical safety buffer. Below this, only use on-demand.
        self.critical_buffer_seconds = self.restart_overhead
        
        # Buffer threshold for deciding to wait (NONE) vs using on-demand.
        self.wait_threshold_buffer_seconds = 4 * self.env.gap_seconds
        
        # Minimum buffer required to consider switching regions.
        self.switch_min_buffer_seconds = self.restart_overhead + self.env.gap_seconds
        
        # --- State tracking for each region ---
        self.region_stats = []
        for _ in range(self.num_regions):
            self.region_stats.append({
                'visits': 0,
                'history': collections.deque(maxlen=self.history_window_size),
                'spot_rate': 1.0,  # Optimistic initialization to encourage exploration
            })
            
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # 1. UPDATE STATE AND STATISTICS
        current_region = self.env.get_current_region()
        stats = self.region_stats[current_region]
        
        stats['visits'] += 1
        stats['history'].append(1 if has_spot else 0)
        stats['spot_rate'] = sum(stats['history']) / len(stats['history'])

        # 2. CALCULATE URGENCY
        remaining_work = self.task_duration - sum(self.task_done_time)

        if remaining_work <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        time_needed_on_demand = remaining_work + self.remaining_restart_overhead
        safety_buffer = time_left - time_needed_on_demand

        # 3. DECISION LOGIC

        # A. CRITICAL (RED ZONE): Not enough time, must use On-Demand.
        if safety_buffer <= self.critical_buffer_seconds:
            return ClusterType.ON_DEMAND

        # B. SPOT AVAILABLE: Always take it if we are not in the critical zone.
        if has_spot:
            return ClusterType.SPOT

        # C. SPOT NOT AVAILABLE: Decide between On-Demand, Wait (None), or Switch.
        
        # C.1. Evaluate switching to another region.
        target_region = -1
        should_switch = False
        
        unvisited_regions = [r for r, s in enumerate(self.region_stats) if s['visits'] == 0]
        if unvisited_regions:
            target_region = unvisited_regions[0]
            should_switch = True
        else:
            best_rate = -1.0
            best_region_idx = -1
            for r, s in enumerate(self.region_stats):
                if r == current_region:
                    continue
                if s['spot_rate'] > best_rate:
                    best_rate = s['spot_rate']
                    best_region_idx = r
            
            if best_region_idx != -1 and \
               best_rate > stats['spot_rate'] + self.rate_improvement_threshold:
                target_region = best_region_idx
                should_switch = True

        # C.2. Make the final action decision.
        if should_switch and safety_buffer > self.switch_min_buffer_seconds:
            self.env.switch_region(target_region)
            return ClusterType.NONE
        else:
            if safety_buffer > self.wait_threshold_buffer_seconds:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND