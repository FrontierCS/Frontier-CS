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
        # Set hyperparameters from parsed arguments, with sane defaults.
        # self.args is populated by the base Strategy class's __init__
        self.max_expected_preemptions = getattr(self.args, 'max_preemptions', 150)
        self.wait_slack_threshold_hours = getattr(self.args, 'wait_slack_hours', 11.0)

        # Initialize state variables for the simulation.
        self.last_completed_work = 0.0
        self.last_tdt_len = 0
        self.wait_slack_threshold_seconds = self.wait_slack_threshold_hours * 3600.0

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
        # --- 1. Calculate current work progress efficiently ---
        if len(self.task_done_time) > self.last_tdt_len:
            new_segments = self.task_done_time[self.last_tdt_len:]
            self.last_completed_work += sum(end - start for start, end in new_segments)
            self.last_tdt_len = len(self.task_done_time)

        completed_work = self.last_completed_work
        work_remaining = max(0.0, self.task_duration - completed_work)
        
        if work_remaining <= 1e-6: # Using a small epsilon for float comparison
            return ClusterType.NONE

        # --- 2. Calculate time metrics ---
        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # --- 3. Define a dynamic safety buffer ---
        if self.task_duration > 0:
            work_progress_ratio = work_remaining / self.task_duration
        else:
            work_progress_ratio = 0.0

        budgeted_preemptions = self.max_expected_preemptions * work_progress_ratio
        safety_buffer = budgeted_preemptions * self.restart_overhead

        # --- 4. Core Decision Logic ---
        
        # Criticality Check: Must we use On-Demand to guarantee completion?
        time_needed_on_demand = work_remaining
        if time_to_deadline <= time_needed_on_demand + safety_buffer:
            return ClusterType.ON_DEMAND

        # Cost-Optimization: If not in a critical state, prioritize low cost.
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot is unavailable. Decide whether to wait or use On-Demand.
            current_slack = time_to_deadline - work_remaining
            if current_slack < self.wait_slack_threshold_seconds:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        """
        Add custom command-line arguments to the parser and instantiate the class.
        """
        parser.add_argument('--max-preemptions', type=int, default=150,
                            help='Estimated maximum number of preemptions to budget for '
                                 'in the safety buffer calculation.')
        parser.add_argument('--wait-slack-hours', type=float, default=11.0,
                            help='Slack threshold in hours. If Spot is unavailable and '
                                 'current slack is below this, use On-Demand instead of waiting.')
        args, _ = parser.parse_known_args()
        return cls(args)
