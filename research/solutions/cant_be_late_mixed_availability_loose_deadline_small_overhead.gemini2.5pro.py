import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    Adaptive Safety Slack Strategy.

    Core Idea:
    1. Always use SPOT instances when available because they are the cheapest way
       to make progress.
    2. When SPOT is unavailable, decide between ON_DEMAND (expensive progress) or
       NONE (free, but no progress).
    3. This decision is based on a "safety slack" calculation. We compare the
       currently available slack time with an estimate of the slack required to
       absorb future disruptions (preemptions).
    4. The required safety slack is dynamically calculated based on an online
       estimate of the spot instance preemption probability.

    Model:
    - We model the spot availability trace as a Markov chain to estimate
      P(preemption) = P(spot becomes unavailable | spot was available).
      This is more accurate than a simple availability average for data with
      temporal correlation (like real-world traces).
    - If current slack > required safety slack, we can afford to wait (NONE).
    - Otherwise, we must use ON_DEMAND to guarantee progress and stay on track.
    - A hard deadline check ensures we switch to ON_DEMAND if we are at the
      absolute point of no return.
    """
    NAME = "AdaptiveSafetySlack"

    def solve(self, spec_path: str) -> "Solution":
        # Hyperparameter for the safety margin. A value > 1.0 makes the
        # strategy more conservative.
        self.safety_margin_factor = 1.5

        # --- State for Markov Chain estimation of preemption probability ---
        # n_from_to: counts of transitions, e.g., n10 is spot -> no_spot
        self.n11 = 0  # spot -> spot
        self.n10 = 0  # spot -> no_spot (preemption)
        
        # State tracking for the previous time step
        self.last_spot_status = None
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # --- 1. Update internal model based on new observation ---
        
        # Update the Markov chain transition counts
        if self.last_spot_status is not None:
            if self.last_spot_status and has_spot:
                self.n11 += 1
            elif self.last_spot_status and not has_spot:
                self.n10 += 1
        
        self.last_spot_status = has_spot

        # --- 2. Calculate current job and time status ---
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        if work_remaining <= 1e-6:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        
        # --- 3. Core Decision Logic ---

        # RULE 1: Hard Deadline (Point of No Return)
        if time_left <= work_remaining:
            return ClusterType.ON_DEMAND

        # RULE 2: Opportunistic Spot Usage
        if has_spot:
            return ClusterType.SPOT

        # RULE 3: Spot is Unavailable - Decide between ON_DEMAND and NONE
        
        # Estimate preemption probability using the Markov model.
        # We use Laplace smoothing (add-1) to avoid division by zero.
        total_spot_transitions = self.n11 + self.n10
        if total_spot_transitions < 1:
            p_preemption = 0.5
        else:
            p_preemption = (self.n10 + 1) / (total_spot_transitions + 2)

        # Calculate the required safety slack.
        expected_overhead_loss = 0.0
        if self.env.gap_seconds > 0:
            steps_to_finish = work_remaining / self.env.gap_seconds
            expected_preemptions = steps_to_finish * p_preemption
            expected_overhead_loss = expected_preemptions * self.restart_overhead

        safety_slack_required = (expected_overhead_loss * self.safety_margin_factor) + self.restart_overhead
        
        current_slack = time_left - work_remaining

        if current_slack > safety_slack_required:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        args, _ = parser.parse_known_args()
        return cls(args)