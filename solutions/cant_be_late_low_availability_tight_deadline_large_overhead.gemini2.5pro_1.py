import argparse
from collections import deque
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    This strategy employs an adaptive threshold based on an online estimation
    of spot instance availability. The core idea is to balance the cost-saving
    of waiting for a cheap spot instance against the risk of consuming too much
    of the time slack before the deadline.

    The strategy operates in several modes:
    1.  **Emergency Mode:** If the remaining time to the deadline is less than
        or equal to the time required to finish the job on a reliable on-demand
        instance (`current_slack <= 0`), it exclusively uses ON_DEMAND to
        guarantee completion.
    2.  **Opportunistic Spot Mode:** If a spot instance is available, it is
        always chosen due to its low cost.
    3.  **Adaptive Wait/Work Mode:** If no spot instance is available, the
        decision to use ON_DEMAND (work) versus NONE (wait) is made based
        on an adaptive slack threshold.
        - An online estimate of spot availability (`p_spot`) is maintained using
          a moving window of recent history.
        - The `slack_threshold` is calculated as the sum of the expected time
          to wait for the next spot instance and a fixed safety buffer. This
          buffer is a multiple of the `restart_overhead` to ensure resilience
          against future preemptions.
        - If the current slack is below this threshold, the strategy switches
          to ON_DEMAND to make progress conservatively.
        - If there is ample slack, it chooses to wait (NONE), saving costs.

    This adaptive approach allows the strategy to be aggressive in saving costs
    when spot availability is high and conservative when it is low, maximizing
    performance across different real-world traces.
    """
    NAME = "adaptive_threshold_strategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the parameters for the adaptive strategy.
        """
        # --- Parameters for spot availability estimation ---
        # A moving window to keep track of recent spot availability.
        self.history_window = deque(maxlen=200)
        # Minimum assumed spot probability, based on problem spec (4-40%).
        self.P_SPOT_MIN = 0.04
        # Initial estimate for spot probability.
        self.p_spot_estimate = self.P_SPOT_MIN
        # Number of steps to observe before starting to update the estimate.
        self.BURN_IN_STEPS = 50

        # --- Parameters for the slack threshold ---
        # A safety factor to ensure we keep a buffer of slack.
        # The buffer is this factor times the restart_overhead.
        # This helps absorb the time cost of future preemptions.
        self.SAFETY_BUFFER_FACTOR = 1.5

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Makes a decision at each time step based on the adaptive strategy.
        """
        # 1. Calculate current state (progress, time, slack)
        total_work_done = sum(end - start for start, end in self.task_done_time)
        remaining_work = self.task_duration - total_work_done

        if remaining_work <= 0:
            return ClusterType.NONE  # Job is done

        current_time = self.env.elapsed_seconds
        time_to_deadline = self.deadline - current_time
        current_slack = time_to_deadline - remaining_work

        # 2. EMERGENCY MODE:
        # If slack is non-positive, we must use ON_DEMAND to finish on time.
        if current_slack <= 0:
            return ClusterType.ON_DEMAND

        # 3. OPPORTUNISTIC SPOT MODE:
        # If spot is available, always take the cheapest option to make progress.
        if has_spot:
            self.history_window.append(1)
            return ClusterType.SPOT
        else:
            self.history_window.append(0)

        # 4. ADAPTIVE WAIT/WORK MODE (when spot is not available):

        # Update the spot availability estimate after a burn-in period.
        if len(self.history_window) > self.BURN_IN_STEPS:
            # The estimate is the mean of the recent history, floored by the
            # pessimistic known minimum to avoid over-optimism.
            self.p_spot_estimate = max(self.P_SPOT_MIN,
                                       sum(self.history_window) / len(self.history_window))

        # Calculate the adaptive slack threshold.
        # Due to the memoryless property of the geometric distribution, the
        # expected number of future trials until a success is 1/p.
        expected_wait_time = (1 / self.p_spot_estimate) * self.env.gap_seconds

        safety_buffer = self.SAFETY_BUFFER_FACTOR * self.restart_overhead
        slack_threshold = expected_wait_time + safety_buffer

        # Decide based on the threshold.
        if current_slack <= slack_threshold:
            # Slack-Poor: Not enough buffer to wait. Use ON_DEMAND.
            return ClusterType.ON_DEMAND
        else:
            # Slack-Rich: Plenty of buffer. Wait for a spot instance.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        Required classmethod for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
