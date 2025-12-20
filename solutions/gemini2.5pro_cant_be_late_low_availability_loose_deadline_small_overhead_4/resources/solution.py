import collections
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    An adaptive strategy that balances cost-saving on spot instances with the risk
    of missing the deadline.

    The strategy operates in two modes:
    1. 'spot_seeking': The default mode. It prefers using Spot instances when
       available. When Spot is unavailable, it decides whether to wait (NONE) or
       use an On-Demand instance based on an adaptive threshold. This threshold
       is a function of historical spot availability and the amount of remaining
       slack time. The more slack is consumed, the less willing the strategy is
       to wait.
    2. 'safe_mode': A fail-safe mode triggered when the remaining slack time
       drops below a predefined safety buffer. In this mode, the strategy uses
       only On-Demand instances to guarantee timely completion of the job.

    This approach aims to maximize the use of cheap Spot instances while there is
    plenty of slack, and pivots to a more conservative, reliable approach as the
    deadline approaches to ensure the job finishes on time.
    """
    NAME = "AdaptiveSlack"

    # --- Hyperparameters ---
    # The slack time buffer (in hours) to reserve. If slack drops below this,
    # switch to 'safe_mode' (always On-Demand).
    SAFE_MODE_SLACK_HOURS = 4.0

    # The time window (in hours) for calculating the moving average of spot
    # availability.
    HISTORY_WINDOW_HOURS = 6.0

    # The minimum historical spot availability required to justify waiting (using
    # NONE) when slack is at its maximum.
    MIN_WAIT_AVAILABILITY = 0.10

    # The maximum historical spot availability required to justify waiting when
    # slack is at its minimum (just before entering safe_mode). This makes the
    # strategy more conservative as slack decreases.
    MAX_WAIT_AVAILABILITY = 0.45

    def __init__(self):
        super().__init__()
        # --- State Variables ---
        self.mode = 'spot_seeking'
        self.spot_history = None
        self.initial_slack = None
        self.history_window_steps = None
        self.safe_mode_slack_seconds = None

    @classmethod
    def _from_args(cls, parser):
        # This method is required by the evaluator to instantiate the class.
        # We don't add any custom command-line arguments.
        args, _ = parser.parse_known_args()
        return cls()

    def solve(self, spec_path: str) -> "Solution":
        # No complex initialization is needed before the simulation starts.
        # State will be lazily initialized in the first _step() call.
        return self

    def _initialize_params(self):
        """
        Lazy initializer called on the first _step.
        Calculates constants based on environment info.
        """
        self.initial_slack = self.deadline - self.task_duration
        self.safe_mode_slack_seconds = self.SAFE_MODE_SLACK_HOURS * 3600

        # Adjust the safety buffer if it's larger than the total initial slack.
        if self.safe_mode_slack_seconds >= self.initial_slack and self.initial_slack > 0:
            self.safe_mode_slack_seconds = self.initial_slack * 0.5

        # Calculate the history window size in number of steps.
        if self.env.gap_seconds > 0:
            steps_per_hour = 3600 / self.env.gap_seconds
            self.history_window_steps = int(self.HISTORY_WINDOW_HOURS * steps_per_hour)
        else:
            # Fallback if gap_seconds is zero.
            self.history_window_steps = 360

        self.spot_history = collections.deque(maxlen=self.history_window_steps)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # One-time initialization on the first step.
        if self.initial_slack is None:
            self._initialize_params()

        # Update spot availability history.
        self.spot_history.append(1 if has_spot else 0)

        # Calculate current progress and remaining work.
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If the task is finished, do nothing to avoid further costs.
        if work_remaining <= 0:
            return ClusterType.NONE

        # Calculate current time and slack.
        time_left_until_deadline = self.deadline - self.env.elapsed_seconds
        current_slack = time_left_until_deadline - work_remaining

        # Check if we should switch to the permanent 'safe_mode'.
        if self.mode == 'spot_seeking' and current_slack < self.safe_mode_slack_seconds:
            self.mode = 'safe_mode'

        # --- Decision Logic ---

        if self.mode == 'safe_mode':
            # In safe mode, always use On-Demand to guarantee completion.
            return ClusterType.ON_DEMAND

        # In 'spot_seeking' mode:
        if has_spot:
            # Always prefer the cheaper Spot instance if it's available.
            return ClusterType.SPOT
        else:
            # Spot is not available. Decide between waiting (NONE) or using On-Demand.
            if not self.spot_history or len(self.spot_history) == 0:
                # No history yet, be conservative and use On-Demand.
                return ClusterType.ON_DEMAND

            # Calculate recent average spot availability.
            avg_availability = sum(self.spot_history) / len(self.spot_history)

            # Calculate the dynamic threshold for waiting.
            # The threshold increases as slack decreases, making us less likely to wait.
            slack_range = self.initial_slack - self.safe_mode_slack_seconds
            if slack_range <= 0:
                slack_ratio = 1.0
            else:
                slack_progress = self.initial_slack - current_slack
                slack_ratio = max(0.0, min(1.0, slack_progress / slack_range))

            threshold_range = self.MAX_WAIT_AVAILABILITY - self.MIN_WAIT_AVAILABILITY
            dynamic_threshold = self.MIN_WAIT_AVAILABILITY + slack_ratio * threshold_range

            if avg_availability >= dynamic_threshold:
                # Historical availability is high enough to justify waiting.
                return ClusterType.NONE
            else:
                # Not worth waiting; use On-Demand to make progress.
                return ClusterType.ON_DEMAND
