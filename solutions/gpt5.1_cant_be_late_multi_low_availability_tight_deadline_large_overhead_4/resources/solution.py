import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "slack_safe_spot_strategy"

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

        # Internal tracking for efficient progress computation
        self._done_seconds = 0.0
        self._last_task_segments = 0
        self._fail_safe = False
        return self

    def _update_done_progress(self) -> None:
        """Incrementally track total work done without summing entire list each step."""
        segments = self.task_done_time
        curr_len = len(segments)
        if curr_len > self._last_task_segments:
            total_new = 0.0
            for i in range(self._last_task_segments, curr_len):
                total_new += segments[i]
            self._done_seconds += total_new
            self._last_task_segments = curr_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Update cached progress
        self._update_done_progress()

        # If task already completed, no need to run further
        if self._done_seconds >= self.task_duration:
            self._fail_safe = True
            return ClusterType.NONE

        # Once we commit to on-demand, we never switch back
        if self._fail_safe:
            return ClusterType.ON_DEMAND

        remaining_work = self.task_duration - self._done_seconds
        time_left = self.deadline - self.env.elapsed_seconds

        if time_left <= 0.0:
            # Out of time; choose on-demand as best-effort
            self._fail_safe = True
            return ClusterType.ON_DEMAND

        # Time to finish if we commit to on-demand now and never switch again
        if self.env.cluster_type == ClusterType.ON_DEMAND:
            overhead_now = self.remaining_restart_overhead
        else:
            overhead_now = self.restart_overhead
        finish_time_if_commit_now = overhead_now + remaining_work

        # Time to finish if we gamble this step (worst-case: waste the entire step),
        # then commit to on-demand next step (paying full restart overhead).
        finish_time_if_delay_one_step = (
            self.env.gap_seconds + self.restart_overhead + remaining_work
        )

        # If even committing now cannot meet the deadline, still choose ON_DEMAND
        if time_left < finish_time_if_commit_now:
            self._fail_safe = True
            return ClusterType.ON_DEMAND

        # If we can only meet the deadline by committing now (not after 1 more step),
        # switch to on-demand and stay there.
        if time_left < finish_time_if_delay_one_step:
            self._fail_safe = True
            return ClusterType.ON_DEMAND

        # It is safe to continue chasing Spot this step.
        if has_spot:
            return ClusterType.SPOT
        else:
            # No Spot available; wait to preserve budget while we still have slack
            return ClusterType.NONE
