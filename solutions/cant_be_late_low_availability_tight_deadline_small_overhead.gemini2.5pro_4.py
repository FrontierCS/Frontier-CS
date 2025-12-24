import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.spot_seen_count = 0.0
        self.no_spot_count = 0.0

        # --- Tunable Heuristic Parameters ---
        # Multiplier for the safety buffer. 1.0 means the buffer is exactly
        # one restart_overhead.
        self.SAFETY_BUFFER_MULTIPLIER = 1.0

        # A risk factor determining how long we're willing to wait for a Spot
        # instance relative to the expected wait time. A higher value means
        # we are more patient and take more risk to save costs.
        self.RISK_FACTOR_K = 3.0

        # A minimum floor for the "wait slack". We will switch to On-Demand
        # if slack drops below this value (plus the safety buffer), regardless
        # of how high spot availability seems. 3600s = 1 hour.
        self.MIN_WAIT_SLACK_SECONDS = 3600.0

        # --- Derived Constants ---
        self.safety_buffer = (
            self.restart_overhead * self.SAFETY_BUFFER_MULTIPLIER
        )
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # 1. Update observations to refine our estimate of spot availability.
        if has_spot:
            self.spot_seen_count += 1.0
        else:
            self.no_spot_count += 1.0
        total_steps = self.spot_seen_count + self.no_spot_count

        # 2. Calculate current state variables.
        work_done = self.get_task_done()
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        
        # 'current_slack' is the amount of time we have left until the deadline,
        # minus the time it would take to finish the remaining work purely on
        # an On-Demand instance.
        current_slack = (self.deadline - current_time) - work_remaining

        # 3. Apply the decision logic.

        # Case 1: Critical Zone. Slack is too low to risk a preemption.
        if current_slack <= self.safety_buffer:
            return ClusterType.ON_DEMAND

        # Case 2: Opportunity Zone. We have slack, and Spot is available.
        if has_spot:
            return ClusterType.SPOT

        # Case 3: Decision Zone. We have slack, but Spot is not available.
        # Decide whether to wait (NONE) or make progress (ON_DEMAND).
        
        # Estimate spot availability using Laplace smoothing.
        estimated_availability = (self.spot_seen_count + 1.0) / (total_steps + 2.0)
        
        # Estimate the average time we'd have to wait.
        expected_wait_time = (1.0 / estimated_availability) * self.env.gap_seconds

        # Determine the 'wait_threshold': the slack level below which we are no
        # longer willing to wait.
        adaptive_wait_buffer = self.RISK_FACTOR_K * expected_wait_time
        wait_threshold = self.safety_buffer + max(
            self.MIN_WAIT_SLACK_SECONDS, adaptive_wait_buffer
        )

        if current_slack > wait_threshold:
            # We have plenty of slack, worth waiting for cheaper Spot.
            return ClusterType.NONE
        else:
            # Slack is below the adaptive threshold. Use On-Demand to make
            # guaranteed progress.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        args, _ = parser.parse_known_args()
        return cls(args)
