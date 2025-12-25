import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_slack_strategy"

    # --- Hyperparameters (in hours) ---
    # Total initial slack is 70h deadline - 48h task = 22 hours.

    # C_DANGER_HOURS: If slack (scaled by work remaining) drops below this,
    # we are in the "danger zone" and must use ON_DEMAND. This value
    # represents the safety buffer we want to maintain against preemptions.
    C_DANGER_HOURS = 12.0

    # C_WAIT_HOURS: If slack (scaled by work remaining) is above this,
    # we are in the "safe zone" and can afford to wait (NONE) for SPOT to
    # become available. The gap between C_DANGER_HOURS and C_WAIT_HOURS
    # defines the "caution zone".
    C_WAIT_HOURS = 20.0

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        # Store initial task duration for calculating work ratio.
        self.initial_task_duration = self.task_duration

        # Convert hyperparameters from hours to seconds for internal calculations.
        self.max_danger_slack = self.C_DANGER_HOURS * 3600.0
        self.max_wait_slack = self.C_WAIT_HOURS * 3600.0

        # Initialize a cache for the work done calculation to ensure
        # _step remains efficient.
        self.cached_work_done = 0.0
        self.cached_task_done_len = 0

        return self

    def _get_work_done(self) -> float:
        """
        Calculates the total amount of work completed so far.
        Uses a cache to avoid re-calculating the sum over the entire
        history at each step, making the operation efficient.
        """
        current_len = len(self.task_done_time)
        if current_len == self.cached_task_done_len:
            return self.cached_work_done

        # Sum up the work from new segments since the last calculation.
        new_segments = self.task_done_time[self.cached_task_done_len:]
        new_work = sum(end - start for start, end in new_segments)

        # Update the cache.
        self.cached_work_done += new_work
        self.cached_task_done_len = current_len

        return self.cached_work_done

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.

        Args:
            last_cluster_type: The cluster type used in the previous step
            has_spot: Whether spot instances are available this step

        Returns:
            ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        work_done = self._get_work_done()
        work_remaining = self.initial_task_duration - work_done

        # If the task is finished, do nothing to minimize cost.
        if work_remaining <= 1e-9:
            return ClusterType.NONE

        # Calculate current slack: the time buffer we have if we were to switch
        # to on-demand for the rest of the task.
        time_to_deadline = self.deadline - self.env.elapsed_seconds
        time_needed_for_od = work_remaining
        current_slack = time_to_deadline - time_needed_for_od

        # Scale thresholds by the proportion of work remaining. This makes the
        # strategy more cautious at the beginning (more risk) and more
        # flexible towards the end.
        work_ratio = max(0.0, work_remaining / self.initial_task_duration)
        danger_slack_threshold = self.max_danger_slack * work_ratio
        wait_slack_threshold = self.max_wait_slack * work_ratio

        # --- Decision Logic ---

        # 1. Danger Zone: If current slack is below the danger threshold,
        # we must use the reliable ON_DEMAND cluster to avoid failing.
        if current_slack < danger_slack_threshold:
            return ClusterType.ON_DEMAND

        # From here, slack is sufficient to consider SPOT.
        if has_spot:
            return ClusterType.SPOT

        # If SPOT is not available, choose between waiting or using ON_DEMAND.

        # 2. Safe Zone: If slack is very high (above the wait threshold),
        # we can afford to wait (NONE) for a SPOT instance to become available.
        if current_slack >= wait_slack_threshold:
            return ClusterType.NONE

        # 3. Caution Zone: Slack is between the danger and wait thresholds.
        # It's not worth spending slack by waiting. Use ON_DEMAND to
        # make progress and preserve our buffer.
        else:
            return ClusterType.ON_DEMAND


    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):  # REQUIRED: For evaluator instantiation
        args, _ = parser.parse_known_args()
        return cls(args)