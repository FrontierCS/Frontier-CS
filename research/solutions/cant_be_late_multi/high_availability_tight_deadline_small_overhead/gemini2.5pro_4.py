import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "Cant-Be-Late"

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
        
        self._history_initialized = False
        return self

    def _initialize_state(self):
        self.num_regions = self.env.get_num_regions()
        
        self.last_spot_seen_time = [-1.0] * self.num_regions
        
        initial_slack = self.deadline - self.task_duration
        
        self.PANIC_THRESHOLD = self.restart_overhead + self.env.gap_seconds
        
        self.WAIT_THRESHOLD = max(self.PANIC_THRESHOLD * 2, initial_slack / 6.0)
        
        self._history_initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._history_initialized:
            self._initialize_state()

        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        if remaining_work <= 0:
            return ClusterType.NONE

        current_region = self.env.get_current_region()
        current_time = self.env.elapsed_seconds
        if has_spot:
            self.last_spot_seen_time[current_region] = current_time
        
        time_remaining = self.deadline - current_time
        time_needed_on_demand = remaining_work + self.remaining_restart_overhead
        slack = time_remaining - time_needed_on_demand

        if slack <= self.PANIC_THRESHOLD:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        
        best_alt_region = -1
        max_seen_time = -1.0
        for r in range(self.num_regions):
            if r != current_region:
                if self.last_spot_seen_time[r] > max_seen_time:
                    max_seen_time = self.last_spot_seen_time[r]
                    best_alt_region = r
        
        is_alt_better = best_alt_region != -1
        should_explore = all(t == -1.0 for t in self.last_spot_seen_time)

        if self.num_regions > 1 and (is_alt_better or should_explore):
            if should_explore:
                region_to_switch = (current_region + 1) % self.num_regions
            else:
                region_to_switch = best_alt_region
            
            self.env.switch_region(region_to_switch)
            return ClusterType.NONE
        else:
            if slack > self.WAIT_THRESHOLD:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND