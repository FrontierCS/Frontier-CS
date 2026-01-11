import json
from argparse import Namespace
import numpy as np

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
        
        # Statistics for each region to feed into the UCB1 algorithm
        self.region_stats = [
            {'seen': 0, 'available': 0} for _ in range(self.num_regions)
        ]
        self.total_steps = 0

        # --- Hyperparameters ---
        
        # If slack drops below this, use On-Demand unconditionally. (2 hours)
        self.CRITICAL_SLACK_SECONDS = 2 * 3600.0
        
        # If no spot is available and slack is above this, wait. Otherwise, use On-Demand. (12 hours)
        self.WAIT_SLACK_SECONDS = 12 * 3600.0
        
        # UCB1 exploration constant.
        self.EXPLORATION_CONSTANT = np.sqrt(2.0)

        return self

    def _get_ucb_score(self, region_idx: int) -> float:
        """
        Calculates the UCB1 score for a given region to balance exploration and exploitation.
        """
        stats = self.region_stats[region_idx]
        
        if stats['seen'] == 0:
            return float('inf')
        
        availability_rate = stats['available'] / stats['seen']
        
        # Add a small epsilon to avoid log(0) if total_steps is 0, though it's incremented first.
        exploration_term = self.EXPLORATION_CONSTANT * np.sqrt(
            np.log(self.total_steps) / stats['seen']
        )
        
        return availability_rate + exploration_term

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        self.total_steps += 1

        # 1. Calculate current work and time state
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done

        if remaining_work <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        current_slack = time_to_deadline - remaining_work
        
        current_region = self.env.get_current_region()

        # 2. Update statistics for the current region
        self.region_stats[current_region]['seen'] += 1
        if has_spot:
            self.region_stats[current_region]['available'] += 1

        # 3. Safety net: Check if we are approaching the deadline
        if current_slack < self.CRITICAL_SLACK_SECONDS:
            return ClusterType.ON_DEMAND

        # 4. Primary choice: Use Spot if available
        if has_spot:
            return ClusterType.SPOT

        # 5. No Spot: Decide whether to switch, wait, or use On-Demand
        scores = [self._get_ucb_score(i) for i in range(self.num_regions)]
        best_region_idx = np.argmax(scores)

        if best_region_idx == current_region:
            # The current region is still the best bet.
            if current_slack > self.WAIT_SLACK_SECONDS:
                # We have a large time buffer, so we can afford to wait.
                return ClusterType.NONE
            else:
                # The time buffer is not large enough to risk waiting. Use On-Demand.
                return ClusterType.ON_DEMAND
        else:
            # Another region looks more promising. Consider switching.
            slack_after_switch = current_slack - self.restart_overhead
            if slack_after_switch < self.CRITICAL_SLACK_SECONDS:
                # Switching is too risky. Stay and use On-Demand.
                return ClusterType.ON_DEMAND
            else:
                # It's safe to switch. Switch and wait one step to observe.
                self.env.switch_region(best_region_idx)
                return ClusterType.NONE