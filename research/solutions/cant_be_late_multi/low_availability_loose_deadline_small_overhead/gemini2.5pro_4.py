import json
from argparse import Namespace
from collections import deque

# These are part of the evaluation environment
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A dynamic, adaptive, multi-region scheduling strategy that learns spot
    availability patterns and makes decisions based on task urgency.
    """

    NAME = "adaptive_scheduler"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """Initialize the solution from the problem specification."""
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Custom initialization for the strategy
        self.num_regions = len(config["trace_files"])

        self.history_window_size = 24
        self.spot_history = {
            i: deque(maxlen=self.history_window_size) for i in range(self.num_regions)
        }
        self.spot_probas = {i: 0.5 for i in range(self.num_regions)}

        # Tunable parameters that control the strategy's risk tolerance
        self.CRITICAL_BUFFER_FACTOR = 1.5
        self.ONDEMAND_BUFFER_FACTOR = 5.0
        self.SWITCH_BUFFER_FACTOR = 10.0
        self.SWITCH_PROB_IMPROVEMENT = 0.2

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """Decide the next action based on the current state."""
        # Calculate current progress and remaining work/time
        current_work_done = sum(self.task_done_time)
        work_left = self.task_duration - current_work_done

        if work_left <= 0.0:
            return ClusterType.NONE  # Task is complete

        time_left = self.deadline - self.env.elapsed_seconds
        current_region = self.env.get_current_region()

        # Learn from the latest spot availability information
        history_q = self.spot_history[current_region]
        history_q.append(1 if has_spot else 0)
        if history_q:
            self.spot_probas[current_region] = sum(history_q) / len(history_q)

        # Determine the time needed to finish safely with on-demand
        needed_overhead_for_od = (
            0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead
        )
        time_needed_od = work_left + needed_overhead_for_od

        # CRITICAL STATE: If deadline is imminent, use On-Demand to guarantee completion.
        critical_buffer = self.restart_overhead * self.CRITICAL_BUFFER_FACTOR
        if time_left <= time_needed_od + critical_buffer:
            return ClusterType.ON_DEMAND

        # SAFE STATE: If there is sufficient time, optimize for cost.
        # Ideal case: Spot is available, use it.
        if has_spot:
            return ClusterType.SPOT

        # Fallback case: Spot is unavailable in the current region.
        # Decide between switching regions, using On-Demand, or waiting.

        # Evaluate switching to a region with better historical spot availability.
        best_alt_region, max_alt_proba = -1, -1.0
        regions_to_check = [
            r for r in range(self.num_regions) if r != current_region
        ]
        for r in regions_to_check:
            if self.spot_probas[r] > max_alt_proba:
                max_alt_proba = self.spot_probas[r]
                best_alt_region = r

        is_promising = (
            best_alt_region != -1
            and max_alt_proba
            > self.spot_probas[current_region] + self.SWITCH_PROB_IMPROVEMENT
        )

        switch_buffer = self.restart_overhead * self.SWITCH_BUFFER_FACTOR
        time_needed_after_switch = work_left + self.restart_overhead
        can_afford_switch = time_left > time_needed_after_switch + switch_buffer

        if is_promising and can_afford_switch:
            self.env.switch_region(best_alt_region)
            return ClusterType.SPOT  # Bet on spot availability in the new region

        # If not switching, decide between using On-Demand or waiting (NONE).
        ondemand_buffer = self.restart_overhead * self.ONDEMAND_BUFFER_FACTOR
        can_afford_to_wait = time_left > time_needed_od + ondemand_buffer

        if can_afford_to_wait:
            return ClusterType.NONE  # Ample slack, wait for spot to save cost
        else:
            # Slack is low, make guaranteed progress with On-Demand
            return ClusterType.ON_DEMAND