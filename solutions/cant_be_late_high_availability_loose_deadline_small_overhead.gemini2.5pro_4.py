import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        # The safety buffer is the key tunable parameter. It represents the minimum
        # amount of slack time we want to maintain. If slack drops below this,
        # we switch to the more reliable On-Demand instances.
        self.safety_buffer_sec = self.args.safety_buffer_hours * 3600.0

        # For efficiency, cache the sum of work done and update it incrementally.
        self._work_done_cache = 0.0
        self._last_task_done_len = 0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.

        Args:
            last_cluster_type: The cluster type used in the previous step
            has_spot: Whether spot instances are available this step

        Returns:
            ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # --- 1. Calculate remaining work ---
        # Incrementally update the total work done for efficiency.
        if len(self.task_done_time) > self._last_task_done_len:
            for i in range(self._last_task_done_len, len(self.task_done_time)):
                start, end = self.task_done_time[i]
                self._work_done_cache += (end - start)
            self._last_task_done_len = len(self.task_done_time)

        work_remaining_sec = self.task_duration - self._work_done_cache

        # If the task is completed, do nothing to save cost.
        if work_remaining_sec <= 0:
            return ClusterType.NONE

        # --- 2. Main decision logic ---
        # Always prioritize Spot instances when available because they are the
        # cheapest option for making progress.
        if has_spot:
            return ClusterType.SPOT

        # If Spot is unavailable, decide between using expensive On-Demand or waiting.
        # This decision is based on the amount of slack time remaining.
        time_available_sec = self.deadline - self.env.elapsed_seconds
        
        # Slack is the extra time we have before the deadline, assuming
        # we work continuously from now on.
        slack_sec = time_available_sec - work_remaining_sec

        if slack_sec < self.safety_buffer_sec:
            # If our time buffer is running low, we can't afford to wait.
            # Use On-Demand to guarantee progress and rebuild our slack.
            return ClusterType.ON_DEMAND
        else:
            # We have sufficient slack. It's more cost-effective to wait (NONE)
            # for Spot to become available again rather than paying for On-Demand.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):  # REQUIRED: For evaluator instantiation
        """
        Adds strategy-specific arguments to the parser for command-line tuning.
        """
        parser.add_argument(
            '--safety-buffer-hours',
            type=float,
            default=4.0,
            help='Safety buffer in hours. If slack time drops below this, '
                 'the strategy switches to On-Demand instances.'
        )
        args, _ = parser.parse_known_args()
        return cls(args)
