import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

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

        # Flag to perform one-time initialization on the first step
        self.initialized = False

        # Strategy hyperparameters
        # Prior for region availability (e.g., 80% availability)
        self.PRIOR_SEEN = 5
        self.PRIOR_AVAILABLE = 4
        # Safety buffer: switch to on-demand if slack is less than this * overhead
        self.SAFETY_BUFFER_FACTOR = 1.5
        # Required score improvement to consider a region switch
        self.SWITCH_SCORE_IMPROVEMENT = 0.2
        # Slack needed to afford a switch: must be > this * overhead
        self.SWITCH_SLACK_FACTOR = 4.0
        # Slack threshold to wait (as a fraction of total task duration)
        self.WAIT_SLACK_DURATION_FRACTION = 0.1
        
        return self

    def _initialize_strategy(self):
        """
        Performs one-time initialization when environment info is available.
        """
        self.num_regions = self.env.get_num_regions()
        self.region_stats = [
            {'seen': self.PRIOR_SEEN, 'available': self.PRIOR_AVAILABLE}
            for _ in range(self.num_regions)
        ]
        self.wait_slack_threshold = self.task_duration * self.WAIT_SLACK_DURATION_FRACTION
        self.initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        if not self.initialized:
            self._initialize_strategy()

        # 1. Update historical stats for the current region
        current_region = self.env.get_current_region()
        stats = self.region_stats[current_region]
        stats['seen'] += 1
        if has_spot:
            stats['available'] += 1

        # 2. Calculate current progress and time remaining
        work_done = sum(self.task_done_time)
        work_rem = self.task_duration - work_done

        if work_rem <= 0:
            return ClusterType.NONE  # Task is complete, do nothing

        time_rem = self.deadline - self.env.elapsed_seconds
        slack = time_rem - work_rem

        # 3. Safety Net: If time is critical, use On-Demand to guarantee completion
        safety_buffer = self.restart_overhead * self.SAFETY_BUFFER_FACTOR
        if slack <= safety_buffer:
            return ClusterType.ON_DEMAND

        # 4. Main Decision Logic
        if has_spot:
            # Spot is available and we are not in a critical situation, so use it.
            return ClusterType.SPOT
        
        # --- From here, has_spot is False ---
        
        # 4a. Evaluate switching to another region
        scores = [
            s['available'] / s['seen'] if s['seen'] > 0 else 0
            for s in self.region_stats
        ]
        current_score = scores[current_region]

        best_alt_region_idx = -1
        max_score = -1.0
        # Find the best alternative region based on historical data
        for i, score in enumerate(scores):
            if i == current_region:
                continue
            if score > max_score:
                max_score = score
                best_alt_region_idx = i

        # Conditions for switching:
        # 1. A significantly better region exists.
        cond_better_region = (best_alt_region_idx != -1 and
                              max_score > current_score + self.SWITCH_SCORE_IMPROVEMENT)
        # 2. There's enough slack to absorb the switching overhead.
        cond_enough_slack = slack > (self.restart_overhead * self.SWITCH_SLACK_FACTOR)

        if cond_better_region and cond_enough_slack:
            self.env.switch_region(best_alt_region_idx)
            # After deciding to switch, we incur an overhead. We choose NONE for the
            # current step's action and let the next step's logic decide what to do
            # in the new region.
            return ClusterType.NONE

        # 4b. If not switching, decide between waiting (NONE) or using On-Demand
        if slack > self.wait_slack_threshold:
            # Plenty of slack, so we can afford to wait for Spot to become available.
            return ClusterType.NONE
        else:
            # Not enough slack to wait, must make progress using On-Demand.
            return ClusterType.ON_DEMAND
