import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A deadline-aware, cost-minimizing strategy for multi-region scheduling.

    Core Logic:
    1. Deadline Assurance ("Panic Mode"): The strategy continuously monitors the
       time remaining versus the work remaining. If the slack time drops below a
       critical safety margin, it unconditionally uses On-Demand instances to
       guarantee progress and avoid the severe penalty for missing the deadline.
       This safety margin is calibrated to the time cost of a single spot preemption.

    2. Cost Minimization ("Normal Mode"): When there is ample slack time, the
       strategy prioritizes using cheap Spot instances.
        - If Spot is available, it is always chosen.
        - If Spot is unavailable, the strategy exhibits patience, waiting for a
          configurable number of time steps (`PATIENCE`) in the hopes that Spot
          availability is transient. This avoids the overhead of a region switch.

    3. Intelligent Region Switching: If Spot remains unavailable beyond the
       patience threshold, the strategy evaluates switching to a different region.
        - It maintains spot availability statistics for all regions.
        - It prioritizes exploring unvisited regions to quickly build a complete
          picture of the environment.
        - Among visited regions, it switches to the one with the best-observed
          spot availability.
        - A switch is only triggered if the target region is significantly
          better than the current one, preventing unstable "flapping" between
          regions with similar performance.
        - To ensure progress and safely gather data after a switch, the first
          action in a new region is to use an On-Demand instance.
    """
    NAME = "my_strategy"

    # --- Strategy Hyperparameters ---
    # Number of consecutive no-spot steps to wait before considering a region switch.
    PATIENCE = 2
    # The required improvement in spot availability probability to justify a switch.
    SWITCH_IMPROVEMENT_MARGIN = 0.05
    # ---

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from the problem specification file.
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

        # Custom initialization after the parent class is set up.
        self.num_regions = self.env.get_num_regions()
        
        # Initialize statistics for each region.
        self.region_stats = [
            {'probes': 0, 'success': 0, 'consecutive_fail': 0}
            for _ in range(self.num_regions)
        ]

        # The safety margin for switching to On-Demand. If slack time drops
        # below this, we enter "panic mode". It's set to the time lost in
        # one failed spot attempt, giving us a one-step buffer.
        self.on_demand_safety_margin = self.env.gap_seconds + self.restart_overhead

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide the next action (which cluster type to use) based on the current state.
        """
        work_done = sum(self.task_done_time)
        work_rem = self.task_duration - work_done

        # If the task is finished, do nothing to save cost.
        if work_rem <= 0:
            return ClusterType.NONE

        time_rem = self.deadline - self.env.elapsed_seconds
        current_region = self.env.get_current_region()

        # --- 1. Update Region Statistics ---
        stats = self.region_stats[current_region]
        stats['probes'] += 1
        if has_spot:
            stats['success'] += 1
            stats['consecutive_fail'] = 0
        else:
            stats['consecutive_fail'] += 1

        # --- 2. Panic Mode Check ---
        # The total work outstanding, including any pending restart overhead.
        effective_work_rem = work_rem + self.remaining_restart_overhead
        
        # If time is running out, we must use On-Demand to guarantee progress.
        if time_rem <= effective_work_rem + self.on_demand_safety_margin:
            return ClusterType.ON_DEMAND

        # --- 3. Normal Mode (Sufficient Slack) ---
        if has_spot:
            # Spot is available and we have slack, so use the cheapest option.
            return ClusterType.SPOT
        
        # Spot is unavailable. Decide whether to wait or switch regions.
        if stats['consecutive_fail'] < self.PATIENCE:
            # Be patient; spot availability might be temporarily low.
            return ClusterType.NONE
        else:
            # Patience has run out. Evaluate switching to a new region.
            return self._find_and_switch_region()

    def _find_and_switch_region(self) -> ClusterType:
        """
        Helper function to find the best alternative region and execute the switch.
        """
        current_region = self.env.get_current_region()
        
        # --- Find the best alternative region ---
        best_alt_region = -1
        best_alt_score = -1.0

        for i in range(self.num_regions):
            if i == current_region:
                continue

            stats = self.region_stats[i]
            # Unexplored regions are given an optimistic score of 1.0 to encourage exploration.
            # Otherwise, use the observed success rate.
            score = 1.0 if stats['probes'] == 0 else (stats['success'] / stats['probes'])
            
            if score > best_alt_score:
                best_alt_score = score
                best_alt_region = i

        # --- Decide whether to switch ---
        current_stats = self.region_stats[current_region]
        current_score = 0.0
        if current_stats['probes'] > 0:
            current_score = current_stats['success'] / current_stats['probes']
        
        # Only switch if the alternative is significantly better to avoid flapping.
        should_switch = (best_alt_region != -1 and
                         best_alt_score > current_score + self.SWITCH_IMPROVEMENT_MARGIN)

        if should_switch:
            self.env.switch_region(best_alt_region)
            # After switching, we are in an uncertain state. Use On-Demand to
            # guarantee progress and gather a data point for the new region.
            return ClusterType.ON_DEMAND
        else:
            # No better region found, or the improvement is not significant. Stay and wait.
            return ClusterType.NONE