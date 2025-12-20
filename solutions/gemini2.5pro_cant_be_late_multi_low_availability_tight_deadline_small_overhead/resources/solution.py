import json
from argparse import Namespace
from collections import deque

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that balances cost-saving on spot instances
    with the need to meet a hard deadline.
    """

    NAME = "cant-be-late"

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
        self.initialized = False
        return self

    def _initialize(self):
        """
        One-time initialization of strategy parameters and state.
        """
        self.num_regions = self.env.get_num_regions()

        # Strategy Parameters
        self.history_window_size = 30
        self.quality_prior = 0.3
        self.quality_threshold_for_switch = 0.5
        self.slack_multiplier_for_switch = 2.0
        self.slack_multiplier_for_od = 1.5

        # State Tracking
        self.spot_history = [
            deque(maxlen=self.history_window_size) for _ in range(self.num_regions)
        ]
        self.initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        if not self.initialized:
            self._initialize()

        # 1. Update knowledge base
        current_region = self.env.get_current_region()
        self.spot_history[current_region].append(has_spot)

        # 2. Calculate remaining work and time
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done

        if work_left <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds

        # 3. PANIC MODE CHECK
        # Calculate the minimum time needed to finish if the next spot attempt fails.
        time_needed_if_failure = (
            work_left + self.restart_overhead + self.env.gap_seconds
        )
        
        if time_left <= time_needed_if_failure:
            return ClusterType.ON_DEMAND

        # 4. NORMAL MODE DECISION
        if has_spot:
            if (last_cluster_type == ClusterType.ON_DEMAND and
                work_left < self.restart_overhead):
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # --- No spot available in the current region ---
        
        # A. Evaluate switching to another region
        qualities = []
        for i in range(self.num_regions):
            history = self.spot_history[i]
            if not history:
                qualities.append(self.quality_prior)
            else:
                qualities.append(sum(history) / len(history))

        best_other_quality = -1.0
        best_other_region_idx = -1
        if self.num_regions > 1:
            # Simple argmax to find the best region to switch to
            for i in range(self.num_regions):
                if i == current_region:
                    continue
                if qualities[i] > best_other_quality:
                    best_other_quality = qualities[i]
                    best_other_region_idx = i

        # 'Slack' is the time buffer we have before entering panic mode.
        slack_time = time_left - time_needed_if_failure

        if (best_other_region_idx != -1 and
            best_other_quality > self.quality_threshold_for_switch and
            slack_time > self.restart_overhead * self.slack_multiplier_for_switch):
            
            self.env.switch_region(best_other_region_idx)
            return ClusterType.NONE

        # B/C. If not switching, choose between On-Demand and waiting (NONE)
        if slack_time < self.restart_overhead * self.slack_multiplier_for_od:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.NONE
