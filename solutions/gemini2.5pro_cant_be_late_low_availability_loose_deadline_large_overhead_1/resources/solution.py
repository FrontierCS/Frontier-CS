import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_heuristic"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        # Initialize counters for estimating spot availability probability.
        # We use a prior to stabilize the estimate at the beginning, assuming
        # a baseline 20% spot availability over 20 hypothetical steps.
        self.prior_steps = 20
        self.prior_spot_count = 4  # 4/20 = 20%

        self.steps_observed = 0
        self.spot_available_observed = 0
        
        # This tuning parameter controls the strategy's "patience". It determines
        # how much slack we require before we are willing to wait (NONE) for a
        # spot instance. A higher value means we are less patient and switch to
        # ON_DEMAND more readily when spot is unavailable. This value was
        # chosen after reasoning about the problem's time and cost parameters.
        self.patience_factor = 10.0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.

        The core strategy is based on calculating the available "slack" time and
        making decisions based on risk zones defined by this slack.

        1. Urgent Zone: If slack is dangerously low (less than a restart
           overhead), we must use On-Demand to guarantee completion.
        2. Safe/Cautious Zone: Otherwise, we have some buffer.
           - If Spot is available, always use it (best cost).
           - If Spot is not available, decide between waiting (NONE) or
             making progress (ON_DEMAND). This decision is based on an
             adaptive threshold that considers the observed probability of
             spot availability. If spot seems rare, we are less willing to wait.
        """
        # 1. Update running estimate of spot availability probability (p_spot)
        self.steps_observed += 1
        if has_spot:
            self.spot_available_observed += 1

        total_steps = self.prior_steps + self.steps_observed
        total_spot_available = self.prior_spot_count + self.spot_available_observed
        p_spot = total_spot_available / total_steps

        # 2. Calculate key metrics
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If the task is finished, do nothing to save costs.
        if work_remaining <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        
        # Slack is the time buffer we have if we were to run the rest of the
        # job on a guaranteed On-Demand instance from this point forward.
        slack_if_od_now = (self.deadline - current_time) - work_remaining

        # 3. Decision Logic based on risk zones
        
        # --- URGENT ZONE ---
        # If remaining slack is less than a restart overhead, any spot preemption
        # would likely cause us to miss the deadline. We must use the reliable
        # On-Demand resource. A small 5% safety margin is added.
        if slack_if_od_now <= self.restart_overhead * 1.05:
            return ClusterType.ON_DEMAND

        # --- SAFE / CAUTIOUS ZONE ---
        # If spot instances are available, it's the most cost-effective choice
        # since we have enough slack to absorb a potential preemption.
        if has_spot:
            return ClusterType.SPOT

        # If spot is not available, choose between waiting (NONE) or paying for
        # progress (ON_DEMAND).
        
        # The decision is based on an adaptive threshold. The threshold is the
        # minimum slack we require to be willing to wait for a spot instance.
        # This threshold increases as our estimate for spot probability (p_spot) decreases.
        # Formula: T = overhead * (1 + patience_factor * (1 - p_spot))
        cautious_slack_threshold = self.restart_overhead * (
            1.0 + self.patience_factor * (1.0 - p_spot)
        )

        if slack_if_od_now <= cautious_slack_threshold:
            # Slack is below our current risk tolerance. It's too risky to wait
            # for a spot instance that may not appear soon. Make progress now.
            return ClusterType.ON_DEMAND
        else:
            # We have sufficient slack. We can afford to wait for the cheaper
            # spot instance to become available.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):  # REQUIRED: For evaluator instantiation
        args, _ = parser.parse_known_args()
        return cls(args)
