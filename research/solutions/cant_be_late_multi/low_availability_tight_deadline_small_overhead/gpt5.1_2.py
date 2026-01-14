import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy."""

    NAME = "my_strategy"

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

        # Internal state initialization
        # These attributes are in seconds as set by the parent class.
        self.num_regions = self.env.get_num_regions()

        self.initial_slack = max(self.deadline - self.task_duration, 0.0)

        max_step = float(self.env.gap_seconds) + float(self.restart_overhead)

        three_hours = 3.0 * 3600.0
        base_buffer = max(three_hours, 2.0 * max_step)

        if self.initial_slack > 0.0:
            from_slack = 0.25 * self.initial_slack
            # Buffer time before switching permanently to on-demand.
            self.buffer_time = min(
                max(base_buffer, from_slack),
                0.9 * self.initial_slack,
            )
        else:
            # No slack: still keep a positive buffer; we will mostly use on-demand.
            self.buffer_time = base_buffer

        idle_margin = max(three_hours, 3.0 * max_step)
        if self.initial_slack > 0.0:
            self.idle_slack_threshold = min(
                self.buffer_time + idle_margin,
                self.initial_slack,
            )
            if self.idle_slack_threshold < self.buffer_time:
                self.idle_slack_threshold = self.buffer_time
        else:
            self.idle_slack_threshold = self.buffer_time

        # Track accumulated completed work to avoid O(n) sum every step.
        self._done_work = 0.0
        self._done_len = 0

        # Once set, always use on-demand.
        self.force_on_demand = False

        return self

    def _update_done_work(self) -> None:
        """Incrementally track total completed work time."""
        segments = self.task_done_time
        if not segments:
            return
        n = len(segments)
        # Accumulate newly added segments.
        for i in range(self._done_len, n):
            self._done_work += segments[i]
        self._done_len = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Update our view of completed work.
        self._update_done_work()

        remaining_work = max(self.task_duration - self._done_work, 0.0)
        if remaining_work <= 0.0:
            # Task finished; no need to run more.
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_left = self.deadline - current_time

        if time_left <= 0.0:
            # Past the deadline; additional work can't help the score.
            return ClusterType.NONE

        slack = time_left - remaining_work

        # If slack is already non-positive, we are behind schedule:
        # switch to aggressive on-demand mode (may still fail but best effort).
        if slack <= 0.0:
            self.force_on_demand = True

        # If we are approaching the deadline, permanently switch to on-demand
        # to guarantee completion assuming any remaining slack.
        if (not self.force_on_demand) and (self.initial_slack > 0.0):
            if slack <= self.buffer_time:
                self.force_on_demand = True

        if self.force_on_demand:
            # Always use on-demand once in fallback mode.
            return ClusterType.ON_DEMAND

        # Pre-fallback, speculative phase using Spot when possible.

        if not has_spot:
            # Spot not available in the current region.
            # If slack is still large enough, we can afford to wait (NONE).
            # Otherwise, start using some on-demand time to maintain progress.
            if slack > self.idle_slack_threshold:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND

        # Spot is available and we are in speculative phase: prefer SPOT.
        return ClusterType.SPOT