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

        # Custom state and parameters
        self.initialized = False
        self.stats = []
        self.num_regions = 0
        self.total_steps = 0

        # Heuristic parameter: How long to wait in a region with no spot
        # before considering a switch, as a multiple of restart_overhead.
        self.PATIENCE_FACTOR = 1.5

        # Heuristic parameter: UCB1 exploration constant.
        self.EXPLORATION_CONSTANT = 1.0

        return self

    def _initialize(self):
        """Lazy initialization on the first call to _step."""
        self.num_regions = self.env.get_num_regions()
        self.stats = [
            {
                'visits': 0,
                'spot_avail': 0,
                'current_unavail_streak': 0,
            }
            for _ in range(self.num_regions)
        ]
        self.initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        if not self.initialized:
            self._initialize()

        self.total_steps += 1

        # 1. Calculate current state
        progress = sum(self.task_done_time)
        remaining_work = self.task_duration - progress

        if remaining_work <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        # Worst-case time needed to finish if we switch to on-demand now.
        time_needed_on_demand = remaining_work + self.restart_overhead

        current_region = self.env.get_current_region()

        # 2. Update statistics for the current region
        self.stats[current_region]['visits'] += 1
        if has_spot:
            self.stats[current_region]['spot_avail'] += 1
            self.stats[current_region]['current_unavail_streak'] = 0
        else:
            self.stats[current_region]['current_unavail_streak'] += 1

        # 3. Decision Logic

        # A. Critical path: Not enough time for anything but On-Demand.
        if time_left <= time_needed_on_demand:
            return ClusterType.ON_DEMAND

        # B. Happy path: Spot is available, use it.
        if has_spot:
            return ClusterType.SPOT

        # C. No spot: Decide whether to stay or switch.
        patience_time = self.restart_overhead * self.PATIENCE_FACTOR
        streak_duration = self.stats[current_region]['current_unavail_streak'] * self.env.gap_seconds

        if self.num_regions > 1 and streak_duration >= patience_time:
            # Patience has run out, time to switch.
            best_region = -1
            max_score = -float('inf')

            for j in range(self.num_regions):
                if j == current_region:
                    continue

                visits = self.stats[j]['visits']
                if visits == 0:
                    # Prioritize unvisited regions for exploration.
                    best_region = j
                    break

                # UCB1 score to balance exploitation and exploration.
                availability_rate = self.stats[j]['spot_avail'] / visits
                # Add a small epsilon to total_steps to avoid log(0) if total_steps is 1
                # Although log(1)=0 is fine, this is safer if total_steps starts at 0.
                log_total_steps = math.log(self.total_steps + 1e-6)
                exploration_bonus = self.EXPLORATION_CONSTANT * math.sqrt(
                    log_total_steps / visits
                )
                score = availability_rate + exploration_bonus

                if score > max_score:
                    max_score = score
                    best_region = j

            if best_region != -1:
                self.env.switch_region(best_region)
                # After switching, ON_DEMAND is the safe choice that guarantees progress.
                return ClusterType.ON_DEMAND

        # D. Stay in the region: Decide between ON_DEMAND and NONE.
        slack = time_left - time_needed_on_demand
        if slack > self.env.gap_seconds:
            # We have enough slack to wait for at least one time step.
            return ClusterType.NONE
        else:
            # Not enough slack to wait, must make progress.
            return ClusterType.ON_DEMAND