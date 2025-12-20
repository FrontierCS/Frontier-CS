import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

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
        
        self.initialized = False
        return self

    def _lazy_init(self):
        self.num_regions = self.env.get_num_regions()
        self.region_last_spot_time = [-1.0] * self.num_regions
        self.region_last_visit_time = [-1.0] * self.num_regions
        self.explore_interval_seconds = 2 * 3600 
        self.initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self.initialized:
            self._lazy_init()
        
        current_time = self.env.elapsed_seconds
        current_region = self.env.get_current_region()

        self.region_last_visit_time[current_region] = current_time
        if has_spot:
            self.region_last_spot_time[current_region] = current_time

        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        time_left_to_deadline = self.deadline - current_time
        current_slack = time_left_to_deadline - work_remaining

        if has_spot:
            min_slack_for_exploration = (2 * self.restart_overhead + self.env.gap_seconds)

            if self.num_regions > 1 and current_slack > min_slack_for_exploration:
                oldest_visit_time = float('inf')
                explore_candidate_region = -1
                for i in range(self.num_regions):
                    if i == current_region:
                        continue
                    if self.region_last_visit_time[i] < oldest_visit_time:
                        oldest_visit_time = self.region_last_visit_time[i]
                        explore_candidate_region = i
                
                if (explore_candidate_region != -1 and
                        (oldest_visit_time == -1 or
                         current_time - oldest_visit_time > self.explore_interval_seconds)):
                    self.env.switch_region(explore_candidate_region)
                    return ClusterType.NONE

            return ClusterType.SPOT

        required_slack_after_switch = self.restart_overhead + self.env.gap_seconds
        required_slack_for_switch = self.restart_overhead + required_slack_after_switch

        if self.num_regions > 1 and current_slack >= required_slack_for_switch:
            best_region_candidate = -1
            most_recent_spot_time = -1.0
            
            for i in range(self.num_regions):
                if i == current_region:
                    continue
                if self.region_last_spot_time[i] > most_recent_spot_time:
                    most_recent_spot_time = self.region_last_spot_time[i]
                    best_region_candidate = i
            
            if best_region_candidate != -1:
                self.env.switch_region(best_region_candidate)
                return ClusterType.NONE
            else:
                oldest_visit_time = float('inf')
                explore_candidate_region = -1
                for i in range(self.num_regions):
                    if i == current_region:
                        continue
                    if self.region_last_visit_time[i] < oldest_visit_time:
                        oldest_visit_time = self.region_last_visit_time[i]
                        explore_candidate_region = i
                
                if explore_candidate_region != -1:
                    self.env.switch_region(explore_candidate_region)
                    return ClusterType.NONE
        
        return ClusterType.ON_DEMAND
