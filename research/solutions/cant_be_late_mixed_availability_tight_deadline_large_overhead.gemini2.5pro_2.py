import collections

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "adaptive_buffer"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        # Defer environment-dependent initialization to the first _step call
        # to ensure self.env is available.
        self._is_initialized = False
        return self

    def _initialize(self):
        """
        One-time initialization on the first call to _step,
        once the environment attributes are available.
        """
        # --- Hyperparameters ---
        # Factor to multiply restart_overhead by for the critical safety buffer.
        CRITICAL_BUFFER_FACTOR = 1.5
        # Safety factor for estimating wait times. We are willing to wait only
        # if our slack is comfortably larger than the expected wait time.
        WAIT_TIME_SAFETY_FACTOR = 3.0
        # Duration of history to consider for spot availability estimation.
        HISTORY_WINDOW_HOURS = 2.0
        # Initial guess for spot availability probability (can be optimistic).
        INITIAL_P_HAT = 0.75

        # Buffer when we must use ON_DEMAND to not miss the deadline.
        # This provides a safety margin against at least one preemption.
        self.critical_buffer = CRITICAL_BUFFER_FACTOR * self.restart_overhead

        # History for estimating spot availability (p_hat).
        window_duration_seconds = HISTORY_WINDOW_HOURS * 3600
        # Ensure window size is at least 1, calculated based on step duration.
        history_window_size = max(1,
                                  int(window_duration_seconds / self.env.gap_seconds))
        self.spot_history = collections.deque(maxlen=history_window_size)

        self.p_hat_estimate = INITIAL_P_HAT

        self._is_initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.
        """
        if not self._is_initialized:
            self._initialize()

        # --- 1. Update state and estimates ---
        self.spot_history.append(1 if has_spot else 0)
        # Update our estimate of spot availability using a simple moving average.
        if len(self.spot_history) > 0:
            self.p_hat_estimate = sum(self.spot_history) / len(self.spot_history)

        # --- 2. Calculate current situation ---
        work_remaining = self.task_duration - self.task_done

        # If the task is already finished, do nothing to save costs.
        if work_remaining <= 0:
            return ClusterType.NONE

        time_remaining_to_deadline = self.deadline - self.env.elapsed_seconds

        # Slack is the time we can afford to not make progress before we risk
        # missing the deadline even with guaranteed On-Demand instances.
        current_slack = time_remaining_to_deadline - work_remaining

        # --- 3. Decision Logic ---

        # A. Emergency Mode: If slack is below our critical safety buffer,
        # we must use On-Demand to guarantee completion. This is the highest priority rule.
        if current_slack <= self.critical_buffer:
            return ClusterType.ON_DEMAND

        # B. Ideal Case: If spot instances are available and we are not in emergency mode,
        # always use them as they are the cheapest option for making progress.
        if has_spot:
            return ClusterType.SPOT

        # C. Dilemma Case: Spot is unavailable. Decide between waiting (NONE) or
        # using expensive On-Demand. This decision is based on comparing our current
        # slack against the estimated time we might have to wait for spot availability.

        # Add a small epsilon to prevent division by zero if p_hat is ever exactly 0.
        p_hat_safe = self.p_hat_estimate + 1e-9

        # Estimate how long we might have to wait for the next spot instance.
        expected_steps_to_wait = 1.0 / p_hat_safe
        expected_time_to_wait = expected_steps_to_wait * self.env.gap_seconds

        # We define a dynamic threshold for waiting. We are only willing to wait
        # if our current slack is comfortably larger than this threshold.
        # The threshold includes the critical buffer plus a safety margin on the expected wait time.
        wait_threshold = self.critical_buffer + WAIT_TIME_SAFETY_FACTOR * expected_time_to_wait

        if current_slack <= wait_threshold:
            # Our slack is too low to risk waiting. The estimated wait time is a
            # significant fraction of our remaining buffer. Use On-Demand.
            return ClusterType.ON_DEMAND
        else:
            # We have enough slack to absorb the potential wait time.
            # It's more cost-effective to wait (NONE) for a cheap spot instance.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        REQUIRED: For evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)