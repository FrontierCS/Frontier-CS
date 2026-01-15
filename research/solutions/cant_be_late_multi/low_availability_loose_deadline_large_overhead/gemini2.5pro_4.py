import json
from argparse import Namespace
import math

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

        num_regions = self.env.get_num_regions()

        # Prior: 1 success, 1 failure => 2 visits, 1 success
        self.visits = [2] * num_regions
        self.successes = [1] * num_regions

        # Hyperparameters
        self.switch_score_margin = 0.25
        self.min_slack_for_switch_factor = 2.5

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        current_region = self.env.get_current_region()
        self.visits[current_region] += 1
        if has_spot:
            self.successes[current_region] += 1

        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # Panic mode check
        work_steps_needed = math.ceil(remaining_work / self.env.gap_seconds)
        time_for_work = work_steps_needed * self.env.gap_seconds
        
        critical_time = time_for_work + self.restart_overhead + self.env.gap_seconds

        if time_to_deadline <= critical_time:
            return ClusterType.ON_DEMAND

        # Normal mode
        if has_spot:
            return ClusterType.SPOT
        else:
            if self.env.get_num_regions() <= 1:
                return ClusterType.ON_DEMAND

            scores = [(self.successes[i] / self.visits[i], i) for i in range(self.env.get_num_regions())]
            best_score, best_region_idx = max(scores)

            if best_region_idx == current_region:
                return ClusterType.ON_DEMAND

            current_score = self.successes[current_region] / self.visits[current_region]

            if best_score < current_score + self.switch_score_margin:
                return ClusterType.ON_DEMAND
            
            time_cost_of_switch = self.env.gap_seconds + self.restart_overhead
            slack_time = time_to_deadline - (time_for_work + self.restart_overhead)

            if slack_time < self.min_slack_for_switch_factor * time_cost_of_switch:
                return ClusterType.ON_DEMAND
            
            self.env.switch_region(best_region_idx)
            return ClusterType.NONE