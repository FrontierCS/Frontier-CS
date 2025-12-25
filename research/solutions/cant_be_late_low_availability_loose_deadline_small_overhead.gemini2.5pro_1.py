from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    # --- Strategy Hyperparameters ---

    # Safety buffer factor for entering "panic mode". The time required
    # to finish on On-Demand is considered as work_remaining * (1 + factor).
    # A larger value is safer (switches to OD earlier) but more expensive.
    PANIC_BUFFER_FACTOR = 0.15

    # Maximum time in seconds to wait for a spot instance to become
    # available before falling back to On-Demand.
    PATIENCE_SECONDS = 3600.0  # 1 hour

    # A factor to determine the critical slack threshold. If current slack
    # drops below (PATIENCE_SECONDS * factor), we stop waiting for spot
    # and switch to On-Demand to make progress.
    CRITICAL_SLACK_FACTOR = 2.0

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy's state. Called once before evaluation.
        """
        # Tracks the last time a spot instance was observed to be available.
        # This is used to determine how long we've been waiting for spot.
        self.last_spot_seen_time = 0.0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decision logic for each time step.
        """
        # --- 1. Calculate current state and key metrics ---
        current_time = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)

        # If the task is already completed, do nothing to minimize cost.
        if work_done >= self.task_duration:
            return ClusterType.NONE

        work_remaining = self.task_duration - work_done
        time_to_deadline = self.deadline - current_time

        # --- 2. Update internal state ---
        if has_spot:
            # If spot is available, reset our wait timer by recording the current time.
            self.last_spot_seen_time = current_time

        # --- 3. Main Decision Logic ---

        # === A. PANIC MODE CHECK ===
        # This is the primary safety mechanism. It checks if we are at risk of
        # missing the deadline.
        safety_buffer = self.PANIC_BUFFER_FACTOR * work_remaining
        time_needed_for_od_finish = work_remaining + safety_buffer

        if time_needed_for_od_finish >= time_to_deadline:
            # We are in the critical window. We cannot risk using spot or
            # waiting. We must use the guaranteed On-Demand resource to
            # ensure we finish before the deadline.
            return ClusterType.ON_DEMAND

        # === B. OPPORTUNISTIC MODE ===
        # If not in panic mode, we have slack to try to save costs.
        if has_spot:
            # Spot is available and we have slack. This is the ideal case.
            return ClusterType.SPOT
        else:
            # Spot is not available. Decide whether to wait (NONE) or
            # make progress with On-Demand.

            # Condition 1: Have we waited longer than our patience threshold?
            time_waited_for_spot = current_time - self.last_spot_seen_time
            is_impatient = time_waited_for_spot > self.PATIENCE_SECONDS

            # Condition 2: Is our slack (buffer time) running critically low?
            current_slack = time_to_deadline - work_remaining
            critical_slack_threshold = self.PATIENCE_SECONDS * self.CRITICAL_SLACK_FACTOR
            is_slack_critical = current_slack < critical_slack_threshold

            if is_impatient or is_slack_critical:
                # Patience has run out or we can no longer afford to wait.
                # Switch to On-Demand to make guaranteed progress.
                return ClusterType.ON_DEMAND
            else:
                # We have sufficient slack and patience. Wait for spot.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        Required classmethod for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)