from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    This strategy uses a slack-based heuristic to decide which cluster type to use.
    The core idea is to calculate the "slack" time, which is the amount of time
    the job can afford to be idle or spend on restart overheads without missing
    the deadline.

    The strategy operates in three zones based on the current slack:

    1. SAFE ZONE: If the slack is large, the strategy is patient and cost-conscious.
       It uses Spot instances when available and waits (NONE) when they are not.

    2. URGENT ZONE: If the slack is critically low, the strategy prioritizes meeting
       the deadline above all else. It uses On-Demand instances to guarantee
       progress, as it cannot afford the risk of a Spot preemption.

    3. MIDDLE ZONE: Between the safe and urgent zones, the strategy balances cost
       and risk. It uses Spot when available but switches to On-Demand if Spot
       is unavailable, ensuring the job always makes progress.

    The thresholds for these zones are calculated once in the `solve` method based
    on the total initial slack and the restart overhead.
    """
    NAME = "slack_based_heuristic"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy's parameters and thresholds before evaluation starts.
        """
        # --- Tunable Parameters ---
        # The multiplier for restart_overhead to define the urgent threshold.
        # A value of 2.5 means we switch to mandatory On-Demand when we cannot
        # afford to survive approximately 2.5 more preemptions.
        self.urgent_preemption_buffer = 2.5

        # The fraction of the initial slack that defines the safe zone.
        # A value of 0.6 means we are in the "safe" zone as long as we have
        # more than 60% of our initial slack remaining.
        self.safe_slack_fraction = 0.6

        # --- Threshold Calculation ---
        self.initial_slack = self.deadline - self.task_duration

        # URGENT_THRESHOLD: If slack drops below this, we must use On-Demand.
        self.urgent_threshold = self.restart_overhead * self.urgent_preemption_buffer

        # SAFE_THRESHOLD: If slack is above this, we can afford to wait for Spot.
        self.safe_threshold = self.initial_slack * self.safe_slack_fraction

        # Edge case: If the initial slack is very small, the urgent threshold might
        # be larger than the safe threshold. This ensures a valid zone ordering.
        if self.urgent_threshold >= self.safe_threshold:
            self.safe_threshold = self.urgent_threshold * 1.01

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Makes a decision at each time step based on the current job state.
        """
        work_done = self.get_work_done()
        remaining_work = self.task_duration - work_done

        # If the task is completed, do nothing to save cost.
        if remaining_work <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_to_deadline = self.deadline - current_time

        # If we are past the deadline, we have already failed. Stop incurring costs.
        if time_to_deadline < 0:
            return ClusterType.NONE

        # Slack = (time left to deadline) - (time needed for remaining work)
        slack = time_to_deadline - remaining_work

        # --- Decision Logic based on Slack Zones ---

        # 1. URGENT ZONE: Critically low slack.
        if slack <= self.urgent_threshold:
            return ClusterType.ON_DEMAND

        # 2. SAFE ZONE: Ample slack.
        if slack > self.safe_threshold:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE

        # 3. MIDDLE ZONE: Must make progress, but can risk Spot.
        else:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        """
        Required method for the evaluator to instantiate the class.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
