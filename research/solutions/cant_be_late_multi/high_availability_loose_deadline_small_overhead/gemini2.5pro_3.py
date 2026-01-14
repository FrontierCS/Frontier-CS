import json
from argparse import Namespace
import math
from typing import Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that balances cost and completion time.

    The strategy operates based on the following principles:
    1.  **Safety First (Panic Mode):** If the remaining time to the deadline is
        critically short, it switches to On-Demand instances to guarantee
        completion, overriding all other logic.
    2.  **Use Spot Aggressively:** When not in panic mode, it defaults to using
        cheaper Spot instances whenever they are available.
    3.  **Intelligent Waiting:** If Spot is unavailable, it calculates the available
        slack time. If there is sufficient slack, it waits (chooses NONE) for
        Spot to potentially become available again, saving costs. Otherwise, it
        uses On-Demand to avoid falling behind schedule.
    4.  **Adaptive Region Switching:** It monitors Spot availability in the current
        region. If Spot is unavailable for a prolonged period, it uses a
        UCB1 (Upper Confidence Bound) algorithm to select a more promising
        region to switch to. This balances exploring new regions with
        exploiting known good ones.
    """

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

        # Custom initialization
        num_regions = self.env.get_num_regions()
        self.step_counter = 0
        self.visits = [0] * num_regions
        self.spot_successes = [0] * num_regions
        self.consecutive_spot_failures = [0] * num_regions

        # --- Tunable Parameters ---
        # Buffer time for panic mode to switch to OD before it's too late.
        self.safety_buffer_seconds = 1.0 * 3600.0

        # Time threshold for spot unavailability before considering a region switch.
        self.consecutive_failure_threshold_seconds = 1.0 * 3600.0

        # Slack threshold for waiting vs. using OD when spot is down.
        self.wait_slack_threshold_steps = 5.0

        # Exploration constant for the UCB1 algorithm.
        self.ucb_exploration_constant = 2**0.5

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        self.step_counter += 1
        current_region = self.env.get_current_region()

        # --- 1. Calculate current state metrics ---
        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # --- 2. Update statistics for the current region ---
        self.visits[current_region] += 1
        if has_spot:
            self.spot_successes[current_region] += 1
            self.consecutive_spot_failures[current_region] = 0
        else:
            self.consecutive_spot_failures[current_region] += 1

        # --- 3. Decision Logic: Panic Mode ---
        # If time is running out, switch to On-Demand to guarantee completion.
        panic_threshold = (remaining_work +
                           self.restart_overhead +
                           self.safety_buffer_seconds)
        if time_to_deadline <= panic_threshold:
            return ClusterType.ON_DEMAND

        # --- 4. Decision Logic: Region Switching ---
        # If the current region has had no spot for too long, consider switching.
        current_downtime = self.consecutive_spot_failures[current_region] * self.env.gap_seconds
        if current_downtime >= self.consecutive_failure_threshold_seconds:
            best_region_idx = self._find_best_region(current_region)

            if best_region_idx is not None:
                self.env.switch_region(best_region_idx)
                # After switching, we can't know spot availability, so use On-Demand
                # to guarantee progress and absorb the restart overhead cost.
                return ClusterType.ON_DEMAND

        # --- 5. Decision Logic: Cluster Selection in Current Region ---
        if has_spot:
            # If spot is available and we are not in panic mode, always use it.
            return ClusterType.SPOT
        else:
            # Spot is not available. Decide whether to wait or use On-Demand.
            slack = time_to_deadline - remaining_work - self.remaining_restart_overhead
            wait_slack_threshold = self.wait_slack_threshold_steps * self.env.gap_seconds

            if slack > wait_slack_threshold:
                # If we have enough slack, wait for spot to recover.
                return ClusterType.NONE
            else:
                # Not enough slack, must make progress with On-Demand.
                return ClusterType.ON_DEMAND

    def _find_best_region(self, current_region: int) -> Optional[int]:
        """
        Finds the best region to switch to using the UCB1 algorithm.
        """
        num_regions = self.env.get_num_regions()
        if num_regions <= 1:
            return None

        best_region_idx = -1
        best_region_score = -1.0

        for i in range(num_regions):
            if i == current_region:
                continue

            if self.visits[i] == 0:
                # Strongly encourage exploring unvisited regions.
                score = float('inf')
            else:
                # UCB1 formula: exploitation + exploration
                avg_availability = self.spot_successes[i] / self.visits[i]
                exploration_bonus = self.ucb_exploration_constant * \
                    (math.log(self.step_counter) / self.visits[i])**0.5
                score = avg_availability + exploration_bonus
            
            if score > best_region_score:
                best_region_score = score
                best_region_idx = i

        return best_region_idx if best_region_idx != -1 else None