import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "slack_based_dynamic_wait"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        # Hyperparameters
        self.SAFETY_CUSHION_MULTIPLIER = 1.1
        self.OUTAGE_PENALTY_FACTOR = 0.25
        
        # State
        self.current_outage_duration = 0.0
        
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
        if has_spot:
            self.current_outage_duration = 0.0
        else:
            self.current_outage_duration += self.env.gap_seconds

        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        time_now = self.env.elapsed_seconds
        time_available_to_deadline = self.deadline - time_now
        
        slack = time_available_to_deadline - work_remaining

        preemption_slack_cost = self.restart_overhead + self.env.gap_seconds
        safety_cushion = self.SAFETY_CUSHION_MULTIPLIER * preemption_slack_cost

        if slack <= safety_cushion:
            return ClusterType.ON_DEMAND
        else:
            if has_spot:
                return ClusterType.SPOT
            else:
                outage_penalty = self.current_outage_duration * self.OUTAGE_PENALTY_FACTOR
                wait_threshold = safety_cushion + self.env.gap_seconds + outage_penalty

                if slack <= wait_threshold:
                    return ClusterType.ON_DEMAND
                else:
                    return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        Instantiates the solution from parsed arguments.
        """
        args, _ = parser.parse_known_args()
        return cls(args)