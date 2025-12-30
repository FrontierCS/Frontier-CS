import collections

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_urgency_scheduler"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy's parameters and state.
        """
        # --- Tunable Parameters ---
        # History window size for estimating spot availability (in number of steps).
        HISTORY_SIZE = 1200
        # The range for our dynamic urgency threshold.
        self.MIN_URGENCY_THRESHOLD = 0.80
        self.MAX_URGENCY_THRESHOLD = 0.95
        # Safety multiplier for the restart overhead.
        self.SAFETY_MULTIPLIER = 1.1

        # --- State for Adaptive Logic ---
        self.history = collections.deque(maxlen=HISTORY_SIZE)
        # Initial guess for spot availability, based on the problem's stated range.
        self.initial_spot_estimate = 0.20

        # --- Pre-calculated constants for efficiency ---
        self.safety_buffer = self.SAFETY_MULTIPLIER * self.restart_overhead

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Makes a scheduling decision at each time step.
        """
        # Update our observation of spot availability
        self.history.append(1 if has_spot else 0)

        # Calculate current job progress and time remaining
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_left = self.deadline - self.env.elapsed_seconds

        # 1. Job Completion: If there is no work left, do nothing.
        if work_remaining <= 0:
            return ClusterType.NONE

        # 2. Inevitable Failure: If not enough time remains even with non-stop
        # On-Demand work, we must use On-Demand.
        if work_remaining >= time_left:
            return ClusterType.ON_DEMAND

        # 3. Critical Risk Assessment: Can we afford a single spot preemption?
        # If the time left is less than the work remaining plus a safety buffer,
        # the risk of using a spot instance is too high.
        is_spot_too_risky = (work_remaining >= time_left - self.safety_buffer)
        if is_spot_too_risky:
            return ClusterType.ON_DEMAND

        # 4. Primary Choice: If spot is available and not too risky, use it.
        if has_spot:
            return ClusterType.SPOT

        # 5. Wait vs. Pay Decision: Spot is unavailable.
        else:
            # Estimate recent spot probability to adapt our patience.
            if len(self.history) < (self.history.maxlen or 1) / 10:
                spot_prob = self.initial_spot_estimate
            else:
                spot_prob = sum(self.history) / len(self.history)

            # Linearly scale the urgency threshold based on spot probability.
            # More available spot -> higher threshold -> more patience.
            urgency_threshold = self.MIN_URGENCY_THRESHOLD + \
                (self.MAX_URGENCY_THRESHOLD - self.MIN_URGENCY_THRESHOLD) * spot_prob

            # Current urgency: ratio of work left to time left.
            current_urgency = work_remaining / time_left

            if current_urgency > urgency_threshold:
                # Our slack is running low. We can't afford to wait.
                return ClusterType.ON_DEMAND
            else:
                # We have enough of a time buffer to wait for a cheaper Spot instance.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        Required classmethod for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)