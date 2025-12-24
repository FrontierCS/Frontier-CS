import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the strategy's hyperparameters and state variables.
        """
        # --- Hyperparameters ---
        # Optimistic initial belief of spot availability to encourage
        # exploring the cheaper spot option early when slack is high.
        self.INITIAL_P_AVAIL = 0.6
        
        # Time window for the Exponential Moving Average (EMA) of spot availability.
        # A 1-hour window balances responsiveness to change with stability.
        self.EMA_WINDOW_SECONDS = 3600
        
        # A non-negotiable safety buffer. If slack falls below this, we switch
        # to On-Demand to guarantee finishing. 2 hours provides a substantial
        # margin for error against a 4-hour initial slack.
        self.SAFETY_BUFFER_SECONDS = 2 * 3600
        
        # Risk aversion factor for waiting. We only wait for spot if our
        # spendable slack is comfortably larger than the expected wait time.
        self.WAIT_RISK_FACTOR = 1.5
        
        # If estimated availability drops below this threshold, we consider
        # spot instances effectively unavailable and not worth waiting for.
        self.MIN_P_AVAIL = 0.02

        # --- State Variables ---
        self.p_avail_ema = self.INITIAL_P_AVAIL
        # Smoothing factor for EMA, computed on the first step.
        self.alpha = None
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decision logic for each time step.
        """
        # One-time initialization of the EMA smoothing factor 'alpha'.
        # This makes the EMA window independent of the simulation's time step size.
        if self.alpha is None:
            if self.env.gap_seconds > 1e-9:
                n_steps_in_window = self.EMA_WINDOW_SECONDS / self.env.gap_seconds
                self.alpha = 2 / (n_steps_in_window + 1)
            else:
                # Fallback for an unlikely gap_seconds=0
                self.alpha = 0.05

        # Update our estimate of spot availability using the EMA.
        is_available_now = 1.0 if has_spot else 0.0
        self.p_avail_ema = self.alpha * is_available_now + (1 - self.alpha) * self.p_avail_ema
        
        # --- State Calculation ---
        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        if work_remaining <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_to_deadline = self.deadline - current_time
        
        # Slack is the time buffer we have compared to finishing on a reliable instance.
        slack = time_to_deadline - work_remaining

        # --- Decision Logic ---

        # 1. Critical Zone: If slack is less than our safety buffer, we must use
        #    the reliable On-Demand instances to avoid failing the deadline.
        if slack < self.SAFETY_BUFFER_SECONDS:
            return ClusterType.ON_DEMAND
        
        # 2. Opportunity Zone: If spot instances are available, using them is the
        #    most cost-effective way to make progress.
        if has_spot:
            return ClusterType.SPOT

        # 3. Discretionary Zone: Spot is unavailable. Decide whether to
        #    wait (NONE) or pay for progress (ON_DEMAND).
        
        # If estimated availability is very low, waiting is likely a losing strategy.
        if self.p_avail_ema < self.MIN_P_AVAIL:
            return ClusterType.ON_DEMAND

        # Estimate the time to wait for a spot instance to become available.
        if self.p_avail_ema < 1e-9:
             expected_wait_time = float('inf')
        else:
             expected_wait_time = self.env.gap_seconds / self.p_avail_ema
        
        # The portion of our slack we are willing to "spend" on waiting.
        spendable_slack = slack - self.SAFETY_BUFFER_SECONDS
        
        # Only wait if our spendable slack is significantly larger than the
        # expected wait time, controlled by the risk factor.
        if spendable_slack > self.WAIT_RISK_FACTOR * expected_wait_time:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        """
        Required classmethod for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
