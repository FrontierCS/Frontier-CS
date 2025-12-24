import collections
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    This strategy aims to minimize cost by prioritizing cheap Spot instances,
    while guaranteeing completion before the deadline by switching to expensive
    On-Demand instances when necessary.

    The core of the strategy is a dynamic decision model based on "slack time".
    Slack is the buffer between the earliest possible completion time (if using
    On-Demand continuously) and the hard deadline.

    Decision logic:
    1. If Spot instances are available, always use them. They are the most
       cost-effective way to make progress while preserving slack.
    2. If Spot is unavailable, the choice is between waiting (NONE) or using
       On-Demand.
       - Waiting is free but consumes slack.
       - On-Demand costs money but preserves slack.
    3. To make this choice, the strategy estimates the expected waiting time for
       a Spot instance to become available again. This is modeled using a
       first-order Markov chain on Spot availability, with transition
       probabilities estimated from a sliding window of recent history.
    4. If the current slack is less than the estimated wait time (with a safety
       margin), the risk of falling behind is too high, so we switch to
       On-Demand. Otherwise, we wait (NONE), saving cost and gambling that
       Spot will return soon.
    5. A pending restart overhead (from Spot preemptions) is tracked and factored
       into the slack calculation, making the strategy more conservative after
       a preemption.
    """
    NAME = "markov_slack_scheduler"

    # --- Tunable Parameters ---
    # Window size for estimating spot availability transition probabilities.
    # A 6-hour window is chosen, assuming 60s steps (6 hours * 60 min/hr * 60s/min / 60s/step = 360 steps)
    WINDOW_SIZE = 360
    # Safety factor for the expected wait time. > 1.0 makes the strategy more
    # conservative, switching to On-Demand earlier.
    SAFETY_FACTOR = 1.5
    # ---

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the strategy's state. Called once before evaluation.
        """
        # Deque to store the recent history of spot availability transitions
        self.transitions = collections.deque(maxlen=self.WINDOW_SIZE)
        
        # Counts of transitions for the Markov model
        # n00: unavailable -> unavailable
        # n01: unavailable -> available
        # n10: available   -> unavailable
        # n11: available   -> available
        self.n00, self.n01, self.n10, self.n11 = 0, 0, 0, 0

        # State tracking
        self.last_has_spot = None
        self.pending_overhead = 0.0
        self.is_done = False
        
        return self

    def _update_counts(self, transition: tuple, delta: int):
        """Helper to increment/decrement transition counts."""
        prev, curr = transition
        if not prev and not curr: self.n00 += delta
        elif not prev and curr: self.n01 += delta
        elif prev and not curr: self.n10 += delta
        elif prev and curr: self.n11 += delta

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Main decision-making logic, called at each time step.
        """
        if self.is_done:
            return ClusterType.NONE

        # 1. Update Markov model statistics from a sliding window
        if self.last_has_spot is not None:
            new_transition = (self.last_has_spot, has_spot)
            
            if len(self.transitions) == self.transitions.maxlen:
                old_transition = self.transitions[0]
                self._update_counts(old_transition, -1)

            self.transitions.append(new_transition)
            self._update_counts(new_transition, 1)

        self.last_has_spot = has_spot

        # 2. Detect preemption and update pending overhead
        if last_cluster_type == ClusterType.SPOT and self.env.cluster_type == ClusterType.NONE:
            self.pending_overhead = self.restart_overhead

        # 3. Calculate current progress and check for completion
        work_done = sum(self.task_done_time)
        work_rem = self.task_duration - work_done

        if work_rem <= 0:
            self.is_done = True
            return ClusterType.NONE

        # 4. Core decision logic based on slack
        time_needed_on_demand = work_rem + self.pending_overhead
        slack = (self.deadline - self.env.elapsed_seconds) - time_needed_on_demand
        
        decision = ClusterType.NONE

        if slack < self.env.gap_seconds: # Keep a minimal 1-step buffer
            # Critical path: We are behind or have no buffer. Must use On-Demand.
            decision = ClusterType.ON_DEMAND
        elif has_spot:
            # Always prefer Spot when available.
            decision = ClusterType.SPOT
        else:
            # Spot is unavailable. Decide between On-Demand and None.
            # Estimate probability of spot becoming available (p01).
            # Use Laplace smoothing to handle zero counts and cold starts.
            p01 = (self.n01 + 1) / (self.n00 + self.n01 + 2)
            
            # Expected wait time for spot to become available
            if p01 < 1e-9: # Avoid division by zero
                expected_wait_time = float('inf')
            else:
                expected_wait_time = self.env.gap_seconds / p01

            # If our slack is less than the expected wait time (with a safety margin),
            # we cannot afford to wait. Use On-Demand.
            if slack < expected_wait_time * self.SAFETY_FACTOR:
                decision = ClusterType.ON_DEMAND
            else:
                decision = ClusterType.NONE
        
        # 5. Finalize state for next step
        if decision in [ClusterType.SPOT, ClusterType.ON_DEMAND]:
            # Using any instance will consume the pending overhead
            self.pending_overhead = 0.0

        return decision

    @classmethod
    def _from_args(cls, parser):
        """Required for evaluator instantiation."""
        args, _ = parser.parse_known_args()
        return cls(args)
