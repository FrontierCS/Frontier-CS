import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    """
    An adaptive strategy for the Cant-Be-Late Scheduling Problem.

    This strategy aims to minimize cost by aggressively using Spot instances
    while maintaining a safety buffer of slack time to guarantee completion
    before the deadline. The buffer size is adaptive, growing larger
    when Spot preemptions are observed, making the strategy more cautious in
    unstable environments.

    Core Logic:
    1.  Calculate `current_slack`: This is the time we can waste (e.g., by
        waiting for Spot or being preempted) and still complete the remaining
        work on time using only On-Demand instances.
        `current_slack = time_to_deadline - work_remaining`

    2.  Maintain an adaptive `safety_buffer`: We switch to a conservative
        strategy (always use On-Demand) if `current_slack` drops below this
        buffer. The buffer grows with each observed preemption.
        `safety_buffer = (BASE_K + num_preemptions * PER_PREEMPTION_K) * restart_overhead`

    3.  Decision Making:
        - If `current_slack <= safety_buffer`: Use ON_DEMAND for guaranteed progress.
        - If `current_slack > safety_buffer`: Be opportunistic.
            - If Spot is available: Use SPOT (cheapest).
            - If Spot is not available: Use NONE (wait).
    """
    NAME = "adaptive_buffer_strategy"

    # The base safety buffer, measured in multiples of restart_overhead.
    # A value of 3.0 means we always reserve enough slack to absorb 3 preemptions.
    BASE_K = 3.0

    # How much to increase the buffer per observed preemption, in multiples
    # of restart_overhead. A value of 0.5 makes the strategy more cautious
    # after each preemption.
    PER_PREEMPTION_K = 0.5

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize strategy-specific state. Called once before evaluation.
        """
        self.preemption_count = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        The main decision-making logic, called at each time step.
        """
        # --- 1. Update State ---

        # Detect if we were preempted in the last step. A preemption is assumed
        # if we chose SPOT but our current cluster is no longer SPOT.
        if last_cluster_type == ClusterType.SPOT and self.env.cluster_type != ClusterType.SPOT:
            self.preemption_count += 1

        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If the job is finished, do nothing to avoid further costs.
        if work_remaining <= 1e-6:  # Use a small epsilon for float comparison
            return ClusterType.NONE

        # --- 2. Calculate Slack and Safety Buffer ---

        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # `current_slack` is the time we can waste and still finish on time
        # if we use On-Demand for all remaining work.
        current_slack = time_to_deadline - work_remaining

        # The safety buffer adapts to the observed environment stability.
        current_k_factor = self.BASE_K + self.preemption_count * self.PER_PREEMPTION_K
        safety_buffer_seconds = current_k_factor * self.restart_overhead

        # --- 3. Make Decision ---

        # If our slack is below the safety buffer, we must be conservative.
        if current_slack <= safety_buffer_seconds:
            # Use On-Demand to guarantee progress and stop slack from decreasing.
            return ClusterType.ON_DEMAND
        else:
            # We have enough slack to be opportunistic.
            if has_spot:
                # Use the cheaper Spot instance.
                return ClusterType.SPOT
            else:
                # Wait for a Spot instance to become available.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        Required classmethod for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
