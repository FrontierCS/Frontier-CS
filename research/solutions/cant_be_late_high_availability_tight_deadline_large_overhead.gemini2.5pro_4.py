import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "two_threshold_slack_policy"

    # --- Strategy Parameters ---
    # Safety factor for the "must use On-Demand" threshold (T_od).
    # T_od = self.restart_overhead * T_OD_FACTOR
    T_OD_FACTOR = 1.0

    # Slack threshold (in seconds) for waiting (T_wait).
    # If Spot is unavailable and slack > T_wait, we wait (NONE).
    # Initial slack is 4 hours (14400s). A value of 7200s (2 hours)
    # means we wait if we have more than half of our initial slack left.
    T_WAIT_SECONDS = 7200.0

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Must return self.
        """
        self.initialized = False
        self.T_od = None
        self.T_wait = self.T_WAIT_SECONDS

        # Optimization: cache work_done to avoid re-calculating the sum every step
        self.cached_work_done = 0.0
        self.cached_segments_count = 0
        return self

    def _initialize(self):
        """
        Initialize thresholds on the first call to _step,
        when environment variables are available.
        """
        self.T_od = self.restart_overhead * self.T_OD_FACTOR
        self.initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.

        The strategy is a two-threshold policy based on "slack".
        Slack = (Time until deadline) - (Time needed to finish work on On-Demand)

        Args:
            last_cluster_type: The cluster type used in the previous step
            has_spot: Whether spot instances are available this step

        Returns:
            ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        if not self.initialized:
            self._initialize()

        # 1. Calculate current progress (using cached values for efficiency)
        new_segments_count = len(self.task_done_time)
        if new_segments_count > self.cached_segments_count:
            new_work = sum(
                end - start
                for start, end in self.task_done_time[self.cached_segments_count :]
            )
            self.cached_work_done += new_work
            self.cached_segments_count = new_segments_count

        work_remaining = self.task_duration - self.cached_work_done

        # If the task is complete, do nothing to save costs.
        if work_remaining <= 0:
            return ClusterType.NONE

        # 2. Calculate available slack
        time_to_deadline = self.deadline - self.env.elapsed_seconds
        slack = time_to_deadline - work_remaining

        # 3. Decision Logic
        
        # DANGER ZONE (slack <= T_od):
        # Slack is critically low. We cannot risk a Spot preemption.
        # Must use On-Demand to guarantee progress.
        if slack <= self.T_od:
            return ClusterType.ON_DEMAND

        # If Spot is available, it's always the preferred choice when we are not
        # in the danger zone, as it's the cheapest way to make progress.
        if has_spot:
            return ClusterType.SPOT
        
        # At this point, Spot is unavailable. The choice is between waiting (NONE)
        # or using the expensive On-Demand.
        
        # SAFE ZONE (slack > T_wait):
        # We have a large slack buffer. We can afford to wait for Spot to
        # become available again.
        if slack > self.T_wait:
            return ClusterType.NONE
        
        # CAUTION ZONE (T_od < slack <= T_wait):
        # Slack is getting low. We are no longer comfortable waiting and
        # burning slack. Use On-Demand to make progress.
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        """
        Required for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)