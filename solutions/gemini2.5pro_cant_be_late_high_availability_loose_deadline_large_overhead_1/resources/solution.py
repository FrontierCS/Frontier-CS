import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    """
    This strategy uses a proportional control approach to balance cost and completion time.
    It defines a "soft deadline" earlier than the hard deadline and tries to stay on a
    linear progress schedule to meet this soft deadline.

    The decision logic is as follows:
    1.  **Panic Mode**: If finishing the remaining work on On-Demand would miss the hard
        deadline, it switches to On-Demand permanently. This is the highest priority rule.
    2.  **Prefer Spot**: If Spot instances are available, always use them, as they are the
        cheapest option to make progress.
    3.  **Scheduled Progress**: If Spot is unavailable, the strategy checks if it's ahead
        of or behind its target schedule.
        - If behind schedule, it uses On-Demand to catch up.
        - If ahead of schedule, it pauses (NONE) to save money, waiting for Spot to
          potentially become available again.
    """
    NAME = "my_solution"

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        """Required for evaluator instantiation."""
        args, _ = parser.parse_known_args()
        return cls(args)

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy. Parameters will be calculated on the first _step call
        once the environment is fully loaded.
        """
        # Strategy parameters to be initialized in the first _step call
        self.r_target = None

        # Hyperparameter: fraction of the total slack to be used as a safety margin.
        # A value of 0.5 means we aim to finish halfway through the available slack time.
        self.safety_margin_factor = 0.5

        # For efficient calculation of work_done
        self.last_work_done = 0.0
        self.last_num_segments = 0

        return self

    def _initialize_params(self):
        """
        Calculates and sets the strategy's parameters based on the task specification.
        This is called once on the first invocation of _step.
        """
        total_slack = self.deadline - self.task_duration

        # Safeguard against negative slack
        if total_slack < 0:
            total_slack = 0

        safety_margin = total_slack * self.safety_margin_factor
        soft_deadline = self.deadline - safety_margin

        # If the soft deadline is in the past or now, we must be aggressive.
        # Aim to finish by the hard deadline in this unlikely edge case.
        if soft_deadline <= 0:
            self.r_target = self.task_duration / self.deadline if self.deadline > 0 else 1.0
        else:
            # The target rate of work completion to meet the soft deadline.
            self.r_target = self.task_duration / soft_deadline

    def _get_work_done(self) -> float:
        """
        Efficiently calculates the total work done by summing only new segments.
        """
        if len(self.task_done_time) > self.last_num_segments:
            new_segments = self.task_done_time[self.last_num_segments:]
            work_done_in_new_segments = sum(end - start for start, end in new_segments)
            self.last_work_done += work_done_in_new_segments
            self.last_num_segments = len(self.task_done_time)
        return self.last_work_done

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decides which cluster type to use for the next time step.
        """
        # One-time initialization of strategy parameters.
        if self.r_target is None:
            self._initialize_params()

        # 1. Get current state from the environment
        elapsed_time = self.env.elapsed_seconds
        work_done = self._get_work_done()

        # If the task is finished, do nothing.
        if work_done >= self.task_duration:
            return ClusterType.NONE

        # 2. PANIC MODE: Check for imminent deadline failure.
        work_remaining = self.task_duration - work_done
        time_to_deadline = self.deadline - elapsed_time

        # If the time required to finish on On-Demand exceeds the time left,
        # we have no choice but to use On-Demand.
        if work_remaining >= time_to_deadline:
            return ClusterType.ON_DEMAND

        # 3. CORE LOGIC: Follow the schedule.
        # Always prefer cheap progress.
        if has_spot:
            return ClusterType.SPOT

        # If Spot is unavailable, decide between On-Demand (catch up) and None (wait).
        target_work_done = self.r_target * elapsed_time

        if work_done < target_work_done:
            # We are behind our internal schedule; use On-Demand to make progress.
            return ClusterType.ON_DEMAND
        else:
            # We are on or ahead of schedule; save money and wait for Spot.
            return ClusterType.NONE
