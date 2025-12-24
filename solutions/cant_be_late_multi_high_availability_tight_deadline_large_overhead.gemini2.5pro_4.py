import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "three_tier_ucb"  # REQUIRED: unique identifier

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

        self.spot_uptime_stats = [{'up': 0, 'total': 0} for _ in range(self.num_regions)]
        self.total_spot_observations = 0
        self.UCB_C = 1.414 

        self.consecutive_spot_failures = [0] * self.num_regions

        self.FAILURE_THRESHOLD_TO_SWITCH = 2
        self.CAUTION_BUFFER_SECONDS = 2 * 3600.0

        self._cached_work_done = 0.0
        self._cached_task_done_len = 0

        return self

    def _get_best_ucb_region(self) -> int:
        """Selects the best region using the UCB1 algorithm."""
        for i in range(self.num_regions):
            if self.spot_uptime_stats[i]['total'] == 0:
                return i

        scores = []
        log_total_obs = math.log(self.total_spot_observations + 1e-6)

        for i in range(self.num_regions):
            stats = self.spot_uptime_stats[i]
            num_pulls = stats['total']
            
            mean_uptime = stats['up'] / num_pulls
            exploration_term = self.UCB_C * ((log_total_obs / num_pulls) ** 0.5)
            score = mean_uptime + exploration_term
            scores.append(score)
        
        if not scores:
            return self.env.get_current_region()

        return max(range(len(scores)), key=scores.__getitem__)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        current_region = self.env.get_current_region()
        self.spot_uptime_stats[current_region]['total'] += 1
        self.total_spot_observations += 1
        if has_spot:
            self.spot_uptime_stats[current_region]['up'] += 1
            self.consecutive_spot_failures[current_region] = 0
        else:
            self.consecutive_spot_failures[current_region] += 1
        
        if len(self.task_done_time) > self._cached_task_done_len:
            self._cached_work_done += sum(self.task_done_time[self._cached_task_done_len:])
            self._cached_task_done_len = len(self.task_done_time)
        work_done = self._cached_work_done
        work_remaining = self.task_duration - work_done
        
        if work_remaining <= 0:
            return ClusterType.NONE

        time_now = self.env.elapsed_seconds
        time_left = self.deadline - time_now
        
        time_to_finish_safely = work_remaining + self.restart_overhead
        if time_left <= time_to_finish_safely:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if self.num_regions > 1 and self.consecutive_spot_failures[current_region] >= self.FAILURE_THRESHOLD_TO_SWITCH:
            best_region = self._get_best_ucb_region()
            if best_region != current_region:
                self.env.switch_region(best_region)
                return ClusterType.ON_DEMAND
        
        time_to_finish_with_caution = work_remaining + self.restart_overhead + self.CAUTION_BUFFER_SECONDS
        if time_left <= time_to_finish_with_caution:
            return ClusterType.ON_DEMAND
        
        return ClusterType.NONE
