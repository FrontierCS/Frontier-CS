import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

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

        self.num_regions = self.env.get_num_regions()
        self.region_stats = [
            {'up': 0, 'down': 0}
            for _ in range(self.num_regions)
        ]

        # --- Tunable Parameters ---
        # Factor for the safety buffer. If on-demand slack is less than this
        # many time steps, switch to on-demand.
        self.safety_buffer_factor = 1.0
        # Required score improvement to justify switching regions.
        self.switch_hysteresis_factor = 1.05
        # Ratio of initial slack. If remaining slack is above this ratio,
        # we can afford to wait (NONE). Below, we must work (ON_DEMAND).
        self.patience_threshold_ratio = 0.5
        # --------------------------

        self.initial_slack = self.deadline - self.task_duration
        if self.initial_slack <= 0:
            self.initial_slack = 1.0  # Avoid division by zero

        return self

    def _get_region_score(self, region_idx: int) -> float:
        """Calculates a region's score based on observed spot availability."""
        stats = self.region_stats[region_idx]
        # Use Bayesian average with a Beta(1,1) prior for robustness
        return (stats['up'] + 1.0) / (stats['up'] + stats['down'] + 2.0)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # 1. Update stats and calculate current state
        current_region = self.env.get_current_region()
        stats = self.region_stats[current_region]
        if has_spot:
            stats['up'] += 1
        else:
            stats['down'] += 1

        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done

        if work_left <= 0:
            return ClusterType.NONE

        # 2. Urgency Check: Must use On-Demand to guarantee completion
        time_left = self.deadline - self.env.elapsed_seconds
        time_needed_on_demand = work_left + self.restart_overhead
        on_demand_slack = time_left - time_needed_on_demand

        safety_buffer = self.env.gap_seconds * self.safety_buffer_factor
        if on_demand_slack <= safety_buffer:
            return ClusterType.ON_DEMAND

        # 3. Best Case: Use available Spot instance
        if has_spot:
            return ClusterType.SPOT

        # 4. No Spot Case: Decide to switch, and whether to wait or use On-Demand
        
        # 4a. Region Selection: Switch if a better region is available
        scores = [self._get_region_score(i) for i in range(self.num_regions)]
        current_score = scores[current_region]
        
        best_other_score = -1.0
        best_other_region = -1
        for i in range(self.num_regions):
            if i == current_region:
                continue
            if scores[i] > best_other_score:
                best_other_score = scores[i]
                best_other_region = i
        
        if best_other_region != -1 and best_other_score > current_score * self.switch_hysteresis_factor:
            self.env.switch_region(best_other_region)

        # 4b. Action Selection: Wait (NONE) or make progress (ON_DEMAND)
        # This decision is based on the remaining slack.
        simple_slack = time_left - work_left
        
        if simple_slack > self.initial_slack * self.patience_threshold_ratio:
            # Plenty of slack left, we can afford to wait for a spot instance.
            return ClusterType.NONE
        else:
            # Slack is running low, we must make progress using on-demand.
            return ClusterType.ON_DEMAND