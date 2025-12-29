import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A dynamic multi-region scheduling strategy that balances cost and deadline.

    Core logic:
    1.  Prioritize Spot instances whenever available to minimize cost.
    2.  Maintain a "slack" buffer. If the time buffer drops below a threshold,
        switch to On-Demand to guarantee progress.
    3.  If a region experiences persistent Spot unavailability, switch to another
        region in a round-robin fashion to explore better availability.
    4.  A "panic mode" engages On-Demand when the deadline is critically close,
        ensuring the task finishes on time even with a potential upcoming failure.
    """

    NAME = "dynamic_slack_strategy"

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

        # Strategy-specific state initialized in the first _step call
        self.consecutive_spot_failures = None

        # --- Hyperparameters ---
        # Number of consecutive hours of spot unavailability before switching region.
        self.FAILURE_THRESHOLD = 2
        # Number of potential future failures (preemptions/switches) to buffer for.
        self.SLACK_BUFFER_FAILURES = 3
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # One-time initialization on the first step
        if self.consecutive_spot_failures is None:
            self.consecutive_spot_failures = [0] * self.env.get_num_regions()

        # 1. Calculate current state
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        # 2. If task is finished, do nothing to save cost.
        if remaining_work <= 0:
            return ClusterType.NONE

        elapsed_time = self.env.elapsed_seconds
        time_left = self.deadline - elapsed_time

        # 3. Panic Mode: If finishing on time is at risk, use On-Demand.
        # This checks if we can afford one more failed time step before we
        # absolutely must use on-demand to guarantee completion.
        cost_of_one_failed_gamble = self.env.gap_seconds + self.restart_overhead
        if time_left <= remaining_work + cost_of_one_failed_gamble:
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()

        # 4. If Spot is available, use it.
        if has_spot:
            self.consecutive_spot_failures[current_region] = 0
            return ClusterType.SPOT

        # --- From here, has_spot is False ---
        
        self.consecutive_spot_failures[current_region] += 1

        # 5. Decide between On-Demand, waiting (None), or switching region.
        # This decision is based on the available time slack.
        slack = time_left - remaining_work
        
        # We require a buffer to handle future, unexpected preemptions or switches.
        required_slack_buffer = self.SLACK_BUFFER_FAILURES * (
            self.restart_overhead + self.env.gap_seconds)

        if slack < required_slack_buffer:
            # Not enough slack to risk waiting or switching. Use On-Demand.
            return ClusterType.ON_DEMAND
        else:
            # We have enough slack to be patient.
            # If spot has been down for too long, explore another region.
            if self.consecutive_spot_failures[current_region] >= self.FAILURE_THRESHOLD:
                # Switch to the next region in a round-robin fashion.
                next_region = (current_region + 1) % self.env.get_num_regions()
                self.env.switch_region(next_region)
                # Reset failure counter for the region we are leaving.
                self.consecutive_spot_failures[current_region] = 0

            # After deciding whether to switch, we wait in this time step.
            return ClusterType.NONE