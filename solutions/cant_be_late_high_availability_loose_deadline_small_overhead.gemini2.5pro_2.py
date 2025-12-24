import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        # The safety buffer for our slack time. If the calculated slack
        # (time_to_deadline - work_to_do) falls below this threshold,
        # we switch to On-Demand instances to ensure completion.
        # A 2-hour buffer is chosen as a robust value to handle potential
        # long spot outages or consecutive preemptions.
        self.slack_threshold: float = 2.0 * 3600.0

        # Caching attributes to avoid re-calculating the total work done
        # at every step, which could be slow if the task is fragmented.
        self._work_done_cache: float = 0.0
        self._task_done_time_len_cache: int = 0
        return self

    def _get_work_done(self) -> float:
        """
        Calculates the total amount of work completed so far.
        Uses a cache to avoid re-summing the entire list of work segments
        at every time step. The cache is invalidated when a new work segment
        is added to self.task_done_time.
        """
        if len(self.task_done_time) > self._task_done_time_len_cache:
            self._work_done_cache = sum(end - start for start, end in self.task_done_time)
            self._task_done_time_len_cache = len(self.task_done_time)
        return self._work_done_cache

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.

        The strategy is as follows:
        1. Calculate remaining work and remaining time to the deadline.
        2. Calculate the current "slack": `time_left - work_left`. This is our safety buffer.
        3. If slack is above a defined threshold (e.g., 2 hours), prioritize cost savings:
           - Use SPOT if available.
           - If SPOT is unavailable, wait (NONE) if doing so doesn't drop the slack below the threshold.
           - Otherwise, use ON_DEMAND for one step to make progress.
        4. If slack is below the threshold, switch to a safe mode:
           - Use ON_DEMAND exclusively to guarantee completion before the deadline.
        5. A fail-safe check ensures that if `work_left >= time_left`, we must use ON_DEMAND.
        """
        work_done = self._get_work_done()
        work_left = self.task_duration - work_done

        if work_left <= 0:
            return ClusterType.NONE

        time_left_to_deadline = self.deadline - self.env.elapsed_seconds

        if work_left >= time_left_to_deadline:
            return ClusterType.ON_DEMAND

        current_slack = time_left_to_deadline - work_left

        if current_slack < self.slack_threshold:
            return ClusterType.ON_DEMAND
        else:
            if has_spot:
                return ClusterType.SPOT
            else:
                if current_slack - self.env.gap_seconds >= self.slack_threshold:
                    return ClusterType.NONE
                else:
                    return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):  # REQUIRED: For evaluator instantiation
        """
        This method is required for the evaluator to instantiate the class.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
