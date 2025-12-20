import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.spot_seen_count = 0
        self.total_steps = 0
        
        # Hyperparameters for the strategy
        # Initial guess for spot availability probability (true range is 4-40%).
        self.p_spot_initial = 0.15
        # Number of steps to observe before trusting the online estimate.
        self.min_steps_for_estimate = 100
        # Safety factor for waiting: wait only if slack > factor * expected_wait_time
        self.safety_factor = 2.0
        # Smallest assumed probability to avoid division by zero.
        self.p_spot_epsilon = 0.01
        
        self.critical_slack_buffer = None
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # --- 1. Update State and Online Estimates ---
        self.total_steps += 1
        if has_spot:
            self.spot_seen_count += 1
        
        # Initialize buffer on the first step when env variables are available.
        if self.critical_slack_buffer is None:
            self.critical_slack_buffer = self.restart_overhead + self.env.gap_seconds

        # --- 2. Calculate Key Metrics ---
        total_work_done = sum(end - start for start, end in self.task_done_time)
        remaining_work = self.task_duration - total_work_done

        if remaining_work <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_to_deadline = self.deadline - current_time

        # Slack is the time buffer we have if we were to switch to on-demand
        # for all remaining work.
        slack = time_to_deadline - remaining_work

        # --- 3. Decision Logic ---
        
        # A) Absolute Deadline Fallback:
        # If slack is critically low, we must use on-demand to avoid failure.
        if slack <= self.critical_slack_buffer:
            return ClusterType.ON_DEMAND

        # B) Opportunistic Spot Usage:
        # If spot is available and we're not in a critical situation, use it.
        if has_spot:
            return ClusterType.SPOT

        # C) Core Trade-off (No Spot Available):
        # Decide whether to spend money (ON_DEMAND) or time-slack (NONE).
        if self.total_steps < self.min_steps_for_estimate:
            p_spot_estimated = self.p_spot_initial
        else:
            p_spot_estimated = max(
                self.spot_seen_count / self.total_steps, self.p_spot_epsilon
            )
        
        # Calculate the expected time to wait for a spot instance.
        expected_wait_steps = 1.0 / p_spot_estimated
        expected_wait_time = expected_wait_steps * self.env.gap_seconds
        
        # Define a safety margin based on the expected wait time.
        safety_margin = self.safety_factor * expected_wait_time

        if slack > safety_margin:
            # We have enough slack to risk waiting for a cheaper spot instance.
            return ClusterType.NONE
        else:
            # Slack is too low to risk waiting. Use on-demand to guarantee progress.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
