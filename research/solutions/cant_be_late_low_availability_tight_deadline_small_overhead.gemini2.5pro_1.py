import collections
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "AdaptiveJIT"

    def __init__(self, args):
        super().__init__(args)
        self.args = args
        self.history = None
        self.p_hat = 0.0

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy's parameters and state.
        """
        # Tunable parameters from command-line arguments or defaults
        self.HISTORY_WINDOW_SIZE = getattr(self.args, 'history_window_size', 120)
        self.BUFFER_WAIT_MULTIPLIER = getattr(self.args, 'buffer_wait_multiplier', 2.0)
        self.BUFFER_RESTART_MULTIPLIER = getattr(self.args, 'buffer_restart_multiplier', 3.0)
        self.MIN_BUFFER_S = getattr(self.args, 'min_buffer_s', 600)
        self.INITIAL_P_HAT = getattr(self.args, 'initial_p_hat', 0.22)

        # State variables
        self.history = collections.deque(maxlen=self.HISTORY_WINDOW_SIZE)
        self.p_hat = self.INITIAL_P_HAT
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Implements the decision logic for each timestep.
        The strategy is a "Just-In-Time" approach with an adaptive safety buffer.
        """
        # 1. Check for task completion
        work_remaining = self.get_work_remaining_seconds()
        if work_remaining <= 0:
            return ClusterType.NONE

        # 2. Update state: estimate spot availability
        self.history.append(1 if has_spot else 0)
        if len(self.history) > 10:  # Wait for sufficient data before updating
            self.p_hat = sum(self.history) / len(self.history)

        # 3. Calculate current situation
        time_elapsed = self.env.elapsed_seconds
        time_left_to_deadline = self.deadline - time_elapsed

        # Slack: The time we can afford to idle and still finish by the deadline
        # using On-Demand instances exclusively from that point on.
        slack = time_left_to_deadline - work_remaining

        # 4. Calculate adaptive safety buffer
        # This buffer represents the minimum slack we want to maintain.

        # a) Buffer for potential future restart overheads
        restart_buffer = self.BUFFER_RESTART_MULTIPLIER * self.restart_overhead

        # b) Buffer for expected wait time until a Spot instance is available
        wait_buffer = 0
        if self.p_hat > 0.01: # Avoid division by zero or near-zero
            expected_wait_time = (1.0 / self.p_hat) * self.env.gap_seconds
            wait_buffer = self.BUFFER_WAIT_MULTIPLIER * expected_wait_time
        else:
            # If observed availability is very low, use a large fixed buffer
            wait_buffer = 3600

        # c) The total buffer is a combination of the above, with a minimum floor
        buffer = max(self.MIN_BUFFER_S, restart_buffer + wait_buffer)

        # 5. Make decision based on slack vs. buffer
        if slack <= buffer:
            # Slack has depleted into our safety margin.
            # Switch to On-Demand for guaranteed progress.
            return ClusterType.ON_DEMAND
        else:
            # We have enough slack to take risks for cost savings.
            if has_spot:
                # Use the cheap Spot instance when available.
                return ClusterType.SPOT
            else:
                # Wait (idle) for a Spot instance to become available.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        Defines command-line arguments for tuning the strategy.
        """
        parser.add_argument("--history-window-size", type=int, default=120,
                            help="Number of past steps to estimate spot availability.")
        parser.add_argument("--buffer-wait-multiplier", type=float, default=2.0,
                            help="Multiplier for expected spot wait time in buffer calc.")
        parser.add_argument("--buffer-restart-multiplier", type=float, default=3.0,
                            help="Multiplier for restart overhead in buffer calc.")
        parser.add_argument("--min-buffer-s", type=int, default=600,
                            help="Minimum safety buffer in seconds.")
        parser.add_argument("--initial-p-hat", type=float, default=0.22,
                            help="Initial guess for spot availability probability.")

        args, _ = parser.parse_known_args()
        return cls(args)