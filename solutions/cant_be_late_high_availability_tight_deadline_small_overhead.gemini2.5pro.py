import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes state variables for the strategy. Called once before evaluation.
        """
        self.total_work_done: float = 0.0
        self.last_task_done_len: int = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Makes a decision at each time step on which cluster type to use.
        This strategy prioritizes cost-saving (by using SPOT or NONE) as long as
        the deadline is not at risk. It switches to reliable ON_DEMAND instances
        only when the available slack time drops below a critical safety buffer.
        """
        # --- 1. Update State ---
        # Efficiently update the total work done by processing only new segments
        # from the task_done_time list.
        if len(self.task_done_time) > self.last_task_done_len:
            for i in range(self.last_task_done_len, len(self.task_done_time)):
                start, end = self.task_done_time[i]
                self.total_work_done += (end - start)
            self.last_task_done_len = len(self.task_done_time)

        # --- 2. Check for Completion ---
        remaining_work = self.task_duration - self.total_work_done
        # Use a small epsilon for robust floating-point comparisons.
        if remaining_work <= 1e-9:
            # Job is finished, so select NONE to stop incurring costs.
            return ClusterType.NONE

        # --- 3. Calculate Key Metrics ---
        current_time = self.env.elapsed_seconds
        remaining_time_to_deadline = self.deadline - current_time

        # "Slack" is the amount of time we can afford to be idle without
        # compromising the deadline. It's our primary resource for saving money.
        current_slack = remaining_time_to_deadline - remaining_work

        # The safety buffer is the minimum slack we must preserve to handle
        # a potential spot preemption and subsequent restart without missing
        # the deadline. It's the time cost of one failure event.
        safety_buffer = self.restart_overhead + self.env.gap_seconds

        # --- 4. Decision Logic ---
        # This is the "Point of No Return". If our slack is less than the
        # safety buffer, we must use a guaranteed resource to make progress.
        if current_slack <= safety_buffer:
            return ClusterType.ON_DEMAND
        else:
            # We have a comfortable amount of slack. We can prioritize saving cost.
            if has_spot:
                # Spot is available and is the cheapest option to make progress.
                return ClusterType.SPOT
            else:
                # Spot is not available. Waiting (NONE) is free, effectively
                # "spending" our slack. This is cheaper than using On-Demand.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        """
        Required classmethod for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
