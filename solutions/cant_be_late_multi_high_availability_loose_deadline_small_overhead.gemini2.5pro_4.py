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
        self._initialized = False
        return self

    def _initialize(self):
        """
        One-time initialization of strategy state.
        """
        self.num_regions = self.env.get_num_regions()
        self.consecutive_no_spot_in_current_region = 0

        if self.env.gap_seconds > 0:
            self.NO_SPOT_SWITCH_THRESHOLD = max(
                1, math.ceil(5 * self.restart_overhead / self.env.gap_seconds)
            )
        else:
            self.NO_SPOT_SWITCH_THRESHOLD = 5

        initial_slack = self.deadline - self.task_duration
        self.WAIT_SLACK_THRESHOLD = 0.15 * initial_slack if initial_slack > 0 else 3600.0

        self._initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        if not self._initialized:
            self._initialize()

        work_rem = self.task_duration - sum(self.task_done_time)
        if work_rem <= 0:
            return ClusterType.NONE

        if has_spot:
            self.consecutive_no_spot_in_current_region = 0
        else:
            self.consecutive_no_spot_in_current_region += 1

        time_left = self.deadline - self.env.elapsed_seconds
        
        time_needed_for_guaranteed_completion = work_rem + self.restart_overhead

        if time_needed_for_guaranteed_completion >= time_left:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        else:
            if self.consecutive_no_spot_in_current_region >= self.NO_SPOT_SWITCH_THRESHOLD:
                current_region = self.env.get_current_region()
                next_region = (current_region + 1) % self.num_regions
                self.env.switch_region(next_region)
                self.consecutive_no_spot_in_current_region = 0

            slack = time_left - time_needed_for_guaranteed_completion
            if slack > self.WAIT_SLACK_THRESHOLD:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND
