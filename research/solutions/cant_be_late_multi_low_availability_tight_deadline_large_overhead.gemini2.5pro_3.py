import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "adaptive_slack_lr_strategy"  # REQUIRED: unique identifier

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

        # Defer environment-dependent initializations to the first _step call
        self.initialized = False
        return self

    def _lazy_init(self):
        """
        Initializes strategy parameters that depend on the environment,
        which is only available during the `_step` method.
        """
        self.num_regions = self.env.get_num_regions()

        # `must_be_safe_slack`: The minimum slack required to risk a Spot preemption.
        # It's the time lost from one preemption event (one failed step + recovery).
        self.must_be_safe_slack = self.env.gap_seconds + self.restart_overhead

        # `slack_to_switch`: The minimum slack required to risk switching regions.
        # It's the cost of a switch plus the safety buffer.
        self.slack_to_switch = self.must_be_safe_slack + self.restart_overhead

        # `patience`: Number of consecutive steps without spot before considering a switch.
        self.patience = 2
        self.consecutive_no_spot_steps = 0

        # State for least-recently-visited switching policy.
        self.last_visited_step = [-1] * self.num_regions
        self.step_counter = 0

        self.initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        if not self.initialized:
            self._lazy_init()

        self.step_counter += 1
        current_region = self.env.get_current_region()
        self.last_visited_step[current_region] = self.step_counter

        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE

        remaining_time = self.deadline - self.env.elapsed_seconds
        slack_time = remaining_time - remaining_work

        # PANIC ZONE: If slack is too low to absorb a single failure,
        # we must use the most reliable option to make guaranteed progress.
        if slack_time <= self.must_be_safe_slack:
            return ClusterType.ON_DEMAND

        # OPPORTUNISTIC ZONE: We have enough slack to tolerate failures.
        # Prioritize using cheap Spot instances.
        if has_spot:
            self.consecutive_no_spot_steps = 0
            return ClusterType.SPOT
        else:
            self.consecutive_no_spot_steps += 1
            
            # Decide whether to switch regions or use On-Demand.
            if (self.consecutive_no_spot_steps >= self.patience and
                    slack_time > self.slack_to_switch):

                # Find the least recently visited region to switch to.
                best_next_region = -1
                min_step = float('inf')
                for i in range(self.num_regions):
                    if i == current_region:
                        continue
                    if self.last_visited_step[i] < min_step:
                        min_step = self.last_visited_step[i]
                        best_next_region = i

                if best_next_region != -1:
                    self.env.switch_region(best_next_region)
                    self.consecutive_no_spot_steps = 0
                    # After switching, a restart overhead is incurred.
                    # We do nothing in this step to avoid additional costs.
                    return ClusterType.NONE

            # If we don't switch (not patient enough or not enough slack),
            # use On-Demand to keep making progress.
            return ClusterType.ON_DEMAND