import json
import collections
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "AdaptiveHedging"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.

        The spec file contains:
        - deadline: deadline in hours
        - duration: task duration in hours
        - overhead: restart overhead in hours
        - trace_files: list of trace file paths (one per region)
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
        
        self.initialized = False
        return self

    def _initialize_strategy(self):
        """
        Initializes strategy-specific attributes on the first call to _step.
        """
        self.num_regions = self.env.get_num_regions()

        # --- Hyperparameters ---
        self.history_len = 12
        self.switch_score_threshold = 0.7
        self.switch_hysteresis = 0.15
        self.switch_slack_factor = 3.0
        self.wait_slack_threshold_hours = 6.0
        self.wait_score_threshold = 0.5

        # --- State Tracking ---
        self.spot_history = [
            collections.deque(maxlen=self.history_len)
            for _ in range(self.num_regions)
        ]
        self.region_scores = [0.85] * self.num_regions

        self.initialized = True

    def _find_best_alternative_region(self):
        """
        Finds the region with the highest availability score, excluding the current one.
        """
        current_region = self.env.get_current_region()
        best_alt_score = -1.0
        best_alt_region = -1

        for i in range(self.num_regions):
            if i == current_region:
                continue
            if self.region_scores[i] > best_alt_score:
                best_alt_score = self.region_scores[i]
                best_alt_region = i

        return best_alt_score, best_alt_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Available attributes:
        - self.env.get_current_region(): Get current region index
        - self.env.get_num_regions(): Get total number of regions
        - self.env.switch_region(idx): Switch to region by index
        - self.env.elapsed_seconds: Current time elapsed
        - self.task_duration: Total task duration needed (seconds)
        - self.deadline: Deadline time (seconds)
        - self.restart_overhead: Restart overhead (seconds)
        - self.task_done_time: List of completed work segments
        - self.remaining_restart_overhead: Current pending overhead

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        if not self.initialized:
            self._initialize_strategy()

        # 1. Update history and score for the current region
        current_region = self.env.get_current_region()
        self.spot_history[current_region].append(1 if has_spot else 0)
        if len(self.spot_history[current_region]) > 0:
            self.region_scores[current_region] = (
                sum(self.spot_history[current_region]) /
                len(self.spot_history[current_region]))

        # 2. Calculate current state variables
        remaining_work = self.task_duration - sum(self.task_done_time)

        if remaining_work <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        
        slack = time_to_deadline - (remaining_work + self.remaining_restart_overhead)

        # 3. PANIC MODE: If slack is too low, use On-Demand to guarantee completion.
        if slack <= self.restart_overhead:
            return ClusterType.ON_DEMAND

        # 4. STANDARD MODE: If spot is available, use it.
        if has_spot:
            return ClusterType.SPOT

        # 5. NO-SPOT MODE: Decide to Switch, Wait, or use On-Demand.
        best_alt_score, best_alt_region = self._find_best_alternative_region()
        current_score = self.region_scores[current_region]
        time_cost_of_failed_switch = self.restart_overhead + self.env.gap_seconds

        if (best_alt_region != -1 and
                best_alt_score > current_score + self.switch_hysteresis and
                best_alt_score > self.switch_score_threshold and
                slack > self.switch_slack_factor * time_cost_of_failed_switch):
            
            self.env.switch_region(best_alt_region)
            return ClusterType.SPOT

        raw_slack = time_to_deadline - remaining_work
        wait_slack_threshold_seconds = self.wait_slack_threshold_hours * 3600.0

        if (raw_slack > wait_slack_threshold_seconds and
                current_score > self.wait_score_threshold):
            return ClusterType.NONE
        
        return ClusterType.ON_DEMAND