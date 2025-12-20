import collections
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    An adaptive strategy that balances cost-saving on Spot instances against the risk
    of missing the deadline.

    The core idea is to maintain a "slack" variable, representing the amount of time
    we can afford to waste (e.g., by being idle or being preempted) and still finish
    on time by switching to a guaranteed On-Demand instance.

    The decision logic is governed by two main thresholds on this slack:

    1.  A fixed `safety_buffer`: If the slack drops below this critical threshold,
        the strategy enters a "panic mode" and exclusively uses On-Demand instances
        to guarantee completion. This buffer is sized to withstand several
        consecutive spot preemptions.

    2.  An adaptive `wait_buffer`: When Spot instances are unavailable, the strategy
        must choose between waiting (cost-free, but consumes slack) and using an
        On-Demand instance (costly, but preserves slack). The decision is made by
        comparing the current slack to this `wait_buffer`. The buffer's size is
        dynamically adjusted based on the recent history of Spot availability.
        - If spot availability has been low, the buffer is large, making the
          strategy switch to On-Demand earlier to avoid wasting slack waiting for
          an unlikely resource.
        - If spot availability has been high, the buffer is small, encouraging
          the strategy to wait longer for the cheap Spot instance to reappear.

    This dual-buffer approach allows the strategy to be aggressive in seeking cost
    savings when there is ample time, while becoming progressively more conservative
    as the deadline approaches or as Spot availability deteriorates.
    """
    NAME = "adaptive_slack_strategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy. Called once before the simulation starts.
        """
        self.initialized = False
        return self

    def _initialize(self):
        """
        Sets up parameters and state variables on the first call to _step.
        This is done here because environment-specific attributes like `gap_seconds`
        are only available within the `_step` context.
        """
        # --- TUNABLE PARAMETERS ---

        # Number of worst-case preemptions the safety buffer should withstand.
        # A single preemption costs `restart_overhead + gap_seconds` from our slack.
        self.SAFETY_BUFFER_PREEMPTIONS = 10

        # This fraction of the initial slack is the maximum we're willing to "risk"
        # by waiting for Spot instances instead of using On-Demand.
        self.MAX_WAIT_SLACK_FRACTION = 0.75

        # Number of recent steps to consider for spot availability estimation.
        self.HISTORY_WINDOW_SIZE = 240

        # A small constant to add to work_rem to be slightly more conservative.
        self.EPSILON_SECONDS = 0.1

        # --- DERIVED PARAMETERS ---
        cost_of_preemption = self.restart_overhead + self.env.gap_seconds
        self.safety_buffer = self.SAFETY_BUFFER_PREEMPTIONS * cost_of_preemption

        initial_slack = self.deadline - self.task_duration
        # Ensure max_wait_slack is not negative if the deadline is tight.
        self.max_wait_slack = max(0, initial_slack * self.MAX_WAIT_SLACK_FRACTION)

        # --- STATE ---
        self.availability_history = collections.deque(maxlen=self.HISTORY_WINDOW_SIZE)

        self.initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Makes a decision at each timestep.
        """
        if not self.initialized:
            self._initialize()

        # Update history of spot availability
        self.availability_history.append(1 if has_spot else 0)

        # Calculate work remaining based on committed work segments
        work_done = sum(end - start for start, end in self.task_done_time)
        work_rem = self.task_duration - work_done

        # If the job is finished, do nothing to avoid further costs.
        if work_rem <= self.EPSILON_SECONDS:
            return ClusterType.NONE

        # Calculate time available and slack
        time_available = self.deadline - self.env.elapsed_seconds

        # Slack is the time we can afford to waste and still finish on time with On-Demand.
        slack = time_available - work_rem

        # --- DECISION LOGIC ---

        # 1. PANIC MODE: If slack falls below our safety buffer, we must use On-Demand
        #    to guarantee finishing before the deadline.
        if slack <= self.safety_buffer:
            return ClusterType.ON_DEMAND

        # 2. OPPORTUNISTIC SPOT: If a Spot instance is available and we are not in
        #    panic mode, it is always the most cost-effective choice to use it.
        if has_spot:
            return ClusterType.SPOT

        # 3. WAIT or ON-DEMAND: Spot is not available. We must decide whether to
        #    use expensive On-Demand or wait (use NONE), which consumes our slack.

        # Estimate recent spot availability
        if len(self.availability_history) > 0:
            p_avail_est = sum(self.availability_history) / len(self.availability_history)
        else:
            p_avail_est = 0.5  # Default assumption before we have data

        # The wait_buffer determines the slack threshold for switching from NONE to ON_DEMAND.
        # It is inversely proportional to the estimated spot availability.
        # If spot seems unavailable (p_avail_est -> 0), wait_buffer is high -> use ON_DEMAND earlier.
        # If spot seems available (p_avail_est -> 1), wait_buffer is low -> wait longer for spot.
        wait_buffer = self.safety_buffer + self.max_wait_slack * (1.0 - p_avail_est)

        if slack <= wait_buffer:
            # Slack is too low to risk waiting, given the recent spot availability trend.
            # Use On-Demand to make guaranteed progress.
            return ClusterType.ON_DEMAND
        else:
            # We have enough slack to wait for Spot to (hopefully) become available again.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        Instantiates the strategy from command-line arguments.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
