from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "dynamic_slack_v1"

    # --- Hyperparameters ---
    # These parameters control the risk-averseness of the strategy.

    # Safety buffer to enter "panic mode" and force On-Demand usage.
    # This is a multiplier for the restart_overhead. It increases linearly
    # with job progress to become more conservative over time.
    INITIAL_SAFETY_FACTOR = 2.0
    FINAL_SAFETY_FACTOR = 5.0

    # Assumed worst-case probability of spot availability. Used to decide
    # whether to wait (NONE) or use On-Demand when spot is unavailable.
    # The problem specifies a 4-40% availability range.
    WORST_CASE_SPOT_P = 0.04

    # A multiplier for the expected wait time cost. This adds a margin of
    # safety to our decision to wait for a spot instance, making the strategy
    # less likely to wait if the slack is not substantial.
    WAIT_RISK_FACTOR = 1.5
    # ---

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        This strategy is stateless between steps, so no setup is needed.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Core decision logic for each time step.

        The strategy is based on a "dynamic slack" calculation. It continuously
        monitors the time buffer available before the deadline and makes
        decisions to keep this buffer above a dynamically adjusting safety margin.

        1.  Calculate Slack: The core metric is `current_slack`, defined as
            the amount of time we would finish ahead of the deadline if we
            switched to reliable On-Demand instances from this point forward.
            `current_slack = (deadline - current_time) - work_remaining`.

        2.  Dynamic Safety Buffer: A `safety_buffer` is calculated. If
            `current_slack` drops below this buffer, the strategy enters a
            "panic mode" and exclusively uses On-Demand to guarantee completion.
            This buffer increases as the job progresses, making the strategy
            more conservative over time.

        3.  Decision Hierarchy:
            - If in "panic mode" (`current_slack <= safety_buffer`), use ON_DEMAND.
            - Otherwise, if Spot is available, use SPOT (the cheapest option).
            - Otherwise (Spot unavailable), decide whether to wait (NONE) or use
              ON_DEMAND. This choice is based on whether the `current_slack` is
              large enough to absorb the potential time lost while waiting for
              Spot to become available again (estimated using a worst-case
              availability probability).
        """
        # 1. Calculate current progress and remaining work/time
        work_done = sum(self.task_done_time)

        # If the job is already finished, do nothing to save costs.
        if work_done >= self.task_duration:
            return ClusterType.NONE

        work_remaining = self.task_duration - work_done
        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # This is the key metric: how much "extra" time we have.
        current_slack = time_to_deadline - work_remaining

        # 2. Determine the dynamic safety buffer for "panic mode"
        if self.task_duration > 0:
            progress_ratio = work_done / self.task_duration
        else:
            progress_ratio = 0
        
        current_safety_factor = self.INITIAL_SAFETY_FACTOR + progress_ratio * (self.FINAL_SAFETY_FACTOR - self.INITIAL_SAFETY_FACTOR)
        safety_buffer = current_safety_factor * self.restart_overhead

        # 3. Decision Logic
        
        # PANIC MODE: If slack is below the safety buffer, we must use On-Demand.
        if current_slack <= safety_buffer:
            return ClusterType.ON_DEMAND

        # HAPPY PATH: If not in panic mode and spot is available, use it.
        if has_spot:
            return ClusterType.SPOT

        # SPOT NOT AVAILABLE: Decide whether to wait (NONE) or use On-Demand.
        if not has_spot:
            # Estimate the time cost of waiting for a spot instance based on the
            # worst-case availability.
            expected_wait_steps = 1.0 / self.WORST_CASE_SPOT_P
            wait_time_risk = (expected_wait_steps *
                              self.env.gap_seconds *
                              self.WAIT_RISK_FACTOR)

            # If we have enough slack to absorb the potential wait time, then wait.
            if current_slack > safety_buffer + wait_time_risk:
                return ClusterType.NONE
            # Otherwise, it's too risky to wait. Use On-Demand to make progress.
            else:
                return ClusterType.ON_DEMAND
        
        # This part of the code should be unreachable, but as a robust fallback,
        # we choose the safest option.
        return ClusterType.ON_DEMAND


    @classmethod
    def _from_args(cls, parser):
        """
        Required classmethod for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)