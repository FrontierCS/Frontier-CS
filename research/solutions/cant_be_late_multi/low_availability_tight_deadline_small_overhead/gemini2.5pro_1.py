import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"

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

        self.consecutive_spot_failures = 0
        
        slack_seconds = self.deadline - self.task_duration
        self.safety_margin = slack_seconds * 0.4
        
        self.num_regions = None

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        if self.num_regions is None:
            self.num_regions = self.env.get_num_regions()

        progress = sum(self.task_done_time)
        remaining_work = self.task_duration - progress

        if remaining_work <= 0:
            return ClusterType.NONE

        time_to_finish_on_demand = remaining_work + self.remaining_restart_overhead
        
        effective_deadline = self.deadline - self.safety_margin
        time_left_to_effective_deadline = effective_deadline - self.env.elapsed_seconds
        is_in_safety_panic = time_to_finish_on_demand >= time_left_to_effective_deadline

        time_left_to_hard_deadline = self.deadline - self.env.elapsed_seconds
        is_in_hard_panic = time_to_finish_on_demand >= time_left_to_hard_deadline

        if is_in_safety_panic or is_in_hard_panic:
            self.consecutive_spot_failures = 0
            return ClusterType.ON_DEMAND

        if has_spot:
            self.consecutive_spot_failures = 0
            return ClusterType.SPOT
        else:
            self.consecutive_spot_failures += 1

            if self.num_regions == 1:
                return ClusterType.ON_DEMAND
            
            if self.consecutive_spot_failures > self.num_regions:
                self.consecutive_spot_failures = 0
                return ClusterType.ON_DEMAND
            else:
                current_region = self.env.get_current_region()
                next_region = (current_region + 1) % self.num_regions
                self.env.switch_region(next_region)
                return ClusterType.SPOT