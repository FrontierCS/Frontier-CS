import argparse
import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        # Initialize state variables
        self.remaining_restart = 0.0
        self.last_decision = ClusterType.NONE
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update restart overhead timer
        if self.remaining_restart > 0:
            self.remaining_restart = max(0.0, self.remaining_restart - self.env.gap_seconds)

        # Check for interruption (spot was used but now unavailable)
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.remaining_restart = self.restart_overhead

        # Calculate progress and remaining work
        completed = sum(end - start for start, end in self.task_done_time)
        remaining_work = max(0.0, self.task_duration - completed)
        remaining_time = self.deadline - self.env.elapsed_seconds
        slack = remaining_time - remaining_work

        # Safety thresholds (in seconds)
        restart_buffer = self.restart_overhead
        urgent_threshold = 2.0 * restart_buffer  # Switch to OD when slack < this
        spot_continue_threshold = 4.0 * restart_buffer  # Continue spot if slack > this
        spot_start_threshold = 6.0 * restart_buffer  # Start spot if slack > this

        # If behind schedule or critically low slack, use on-demand
        if slack <= 0.0 or slack < urgent_threshold:
            self.last_decision = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND

        # If currently in spot session and spot available with sufficient buffer, continue
        if (last_cluster_type == ClusterType.SPOT and has_spot and
                slack > spot_continue_threshold):
            self.last_decision = ClusterType.SPOT
            return ClusterType.SPOT

        # Consider starting new spot instance
        if (has_spot and self.remaining_restart == 0.0 and
                slack > spot_start_threshold):
            self.last_decision = ClusterType.SPOT
            return ClusterType.SPOT

        # Otherwise wait (no cost)
        self.last_decision = ClusterType.NONE
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)