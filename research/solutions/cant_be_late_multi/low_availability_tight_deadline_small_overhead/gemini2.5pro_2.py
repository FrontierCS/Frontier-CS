import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

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
        self.ema_alpha = 0.3
        self.panic_buffer_factor = 1.5
        self.switch_slack_buffer_factor = 3.0
        self.initial_optimism = 0.8
        self.switch_rate_floor = 0.5
        
        self.num_regions = 0
        self.region_availability_rate = []
        self.region_observations = []
        
        return self

    def _initialize_state(self):
        if not self.initialized:
            self.num_regions = self.env.get_num_regions()
            self.region_availability_rate = [self.initial_optimism] * self.num_regions
            self.region_observations = [0] * self.num_regions
            self.initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_state()

        current_region = self.env.get_current_region()
        current_observation = 1.0 if has_spot else 0.0
        self.region_availability_rate[current_region] = (
            self.ema_alpha * current_observation +
            (1 - self.ema_alpha) * self.region_availability_rate[current_region]
        )

        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE

        time_needed_guaranteed = remaining_work + self.remaining_restart_overhead
        time_left_to_deadline = self.deadline - self.env.elapsed_seconds
        
        panic_buffer = self.panic_buffer_factor * self.restart_overhead
        
        if time_left_to_deadline <= time_needed_guaranteed + panic_buffer:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        else:
            best_alt_region_idx = -1
            max_availability_rate = -1.0
            for i in range(self.num_regions):
                if i == current_region:
                    continue
                if self.region_availability_rate[i] > max_availability_rate:
                    max_availability_rate = self.region_availability_rate[i]
                    best_alt_region_idx = i

            current_slack = time_left_to_deadline - time_needed_guaranteed
            switch_overhead_buffer = self.switch_slack_buffer_factor * self.restart_overhead

            should_switch = (
                best_alt_region_idx != -1 and
                max_availability_rate > self.switch_rate_floor and
                max_availability_rate > self.region_availability_rate[current_region] and
                current_slack > switch_overhead_buffer
            )

            if should_switch:
                self.env.switch_region(best_alt_region_idx)
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND