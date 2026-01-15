import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "AdaptiveMultiRegion"

    def solve(self, spec_path: str) -> "Solution":
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
        self.spot_counts = [0] * num_regions
        self.total_counts = [0] * num_regions

        self.consecutive_spot_misses = 0
        self.last_region_idx = -1

        self.SWITCH_MISS_THRESHOLD = 3
        initial_slack = self.deadline - self.task_duration
        self.SLACK_OD_THRESHOLD = initial_slack / 3.0
        self.PROB_SWITCH_TOLERANCE = 0.05

        self.work_done_cache = 0.0
        self.task_done_len_cache = 0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()

        if current_region != self.last_region_idx:
            self.consecutive_spot_misses = 0
            self.last_region_idx = current_region

        self.total_counts[current_region] += 1
        if has_spot:
            self.spot_counts[current_region] += 1
            self.consecutive_spot_misses = 0
        else:
            self.consecutive_spot_misses += 1

        if len(self.task_done_time) > self.task_done_len_cache:
            new_work = sum(self.task_done_time[self.task_done_len_cache:])
            self.work_done_cache += new_work
            self.task_done_len_cache = len(self.task_done_time)
        work_done = self.work_done_cache
        work_left = self.task_duration - work_done

        if work_left <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds

        safety_margin = self.env.gap_seconds
        if time_left <= work_left + safety_margin:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if self.consecutive_spot_misses >= self.SWITCH_MISS_THRESHOLD:
            unvisited = [
                i for i, c in enumerate(self.total_counts)
                if c == 0 and i != current_region
            ]
            if unvisited:
                self.env.switch_region(unvisited[0])
                return ClusterType.ON_DEMAND

            best_region_to_switch = -1
            # Handle division by zero if total_counts is 0 (though checked by `unvisited`)
            if self.total_counts[current_region] > 0:
                current_prob = self.spot_counts[current_region] / self.total_counts[current_region]
            else:
                current_prob = 0.0
            
            max_prob = current_prob
            
            for i in range(self.env.get_num_regions()):
                if i == current_region:
                    continue
                
                if self.total_counts[i] > 0:
                    prob = self.spot_counts[i] / self.total_counts[i]
                    if prob > max_prob + self.PROB_SWITCH_TOLERANCE:
                        max_prob = prob
                        best_region_to_switch = i
            
            if best_region_to_switch != -1:
                self.env.switch_region(best_region_to_switch)
                return ClusterType.ON_DEMAND

        slack = time_left - work_left
        if slack < self.SLACK_OD_THRESHOLD:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.NONE