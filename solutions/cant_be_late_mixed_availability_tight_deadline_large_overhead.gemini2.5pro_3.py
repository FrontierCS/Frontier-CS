import os
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "buffer_based_strategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        self.DANGER_THRESHOLD_MULTIPLIER = 1.1
        self.WAIT_THRESHOLD_MULTIPLIER = 3.0

        self.cached_work_done = 0.0
        self.cached_len_task_done_time = 0
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
        # --- 1. Calculate current state ---
        if len(self.task_done_time) > self.cached_len_task_done_time:
            new_segments = self.task_done_time[self.cached_len_task_done_time:]
            self.cached_work_done += sum(end - start for start, end in new_segments)
            self.cached_len_task_done_time = len(self.task_done_time)
        work_done = self.cached_work_done

        work_remaining = self.task_duration - work_done

        if work_remaining <= 1e-9:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # --- 2. Handle the absolute deadline constraint ---
        if time_to_deadline <= work_remaining:
            return ClusterType.ON_DEMAND

        # --- 3. Implement the buffer-based strategy ---
        buffer = time_to_deadline - work_remaining
        preemption_time_cost = self.restart_overhead + self.env.gap_seconds

        danger_threshold = preemption_time_cost * self.DANGER_THRESHOLD_MULTIPLIER
        if buffer <= danger_threshold:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        wait_threshold = preemption_time_cost * self.WAIT_THRESHOLD_MULTIPLIER
        if buffer > wait_threshold:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):  # REQUIRED: For evaluator instantiation
        args, _ = parser.parse_known_args()
        return cls(args)
