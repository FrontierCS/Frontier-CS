import collections

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    # --- Hyperparameters ---
    # If slack is less than this multiple of restart_overhead, force On-Demand.
    CRITICAL_THRESHOLD_RATIO = 1.2
    # When deciding to wait, slack must be > (expected_wait * factor) + critical_buffer.
    WAIT_SAFETY_FACTOR = 1.5
    # Length of the moving average window for spot availability (in steps).
    HISTORY_LEN = 720
    # Minimum number of historical data points before trusting the availability estimate.
    MIN_HISTORY_FOR_ESTIMATE = 60
    # If estimated availability is below this, don't bother waiting.
    MIN_AVAILABILITY_TO_WAIT = 0.02

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy's state before the simulation begins.
        """
        self.critical_buffer = self.restart_overhead * self.CRITICAL_THRESHOLD_RATIO
        
        # State for maintaining a moving average of spot availability.
        self.spot_history = collections.deque(maxlen=self.HISTORY_LEN)
        self.spot_history_sum = 0
        
        # Caching for efficient calculation of total work done.
        self.work_done_cache = 0.0
        self.last_done_len = 0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        The main decision-making logic, called at each time step.
        """
        # 1. Update the moving average of spot availability.
        is_spot_available = 1 if has_spot else 0
        if len(self.spot_history) == self.HISTORY_LEN:
            self.spot_history_sum -= self.spot_history[0]
        self.spot_history.append(is_spot_available)
        self.spot_history_sum += is_spot_available

        # 2. Calculate current work progress and remaining slack.
        if len(self.task_done_time) > self.last_done_len:
            for i in range(self.last_done_len, len(self.task_done_time)):
                self.work_done_cache += self.task_done_time[i]['duration']
            self.last_done_len = len(self.task_done_time)
        work_done = self.work_done_cache
        
        work_rem = self.task_duration - work_done

        # If the task is finished, do nothing.
        if work_rem <= 0:
            return ClusterType.NONE

        time_rem = self.deadline - self.env.elapsed_seconds
        current_slack = time_rem - work_rem

        # 3. Core Decision Logic.
        # 3a. Emergency Mode: If slack is critically low, use On-Demand.
        if current_slack < self.critical_buffer:
            return ClusterType.ON_DEMAND

        # 3b. Ideal Case: If spot is available, always use it.
        if has_spot:
            return ClusterType.SPOT
        
        # 3c. Dilemma: No spot available. Decide between On-Demand and waiting (NONE).
        if len(self.spot_history) < self.MIN_HISTORY_FOR_ESTIMATE:
            return ClusterType.ON_DEMAND
            
        spot_availability = self.spot_history_sum / len(self.spot_history)

        if spot_availability < self.MIN_AVAILABILITY_TO_WAIT:
            return ClusterType.ON_DEMAND
            
        expected_wait_steps = 1.0 / spot_availability
        expected_wait_time = self.env.gap_seconds * expected_wait_steps
        
        required_slack_to_wait = (expected_wait_time * self.WAIT_SAFETY_FACTOR) + self.critical_buffer
        
        if current_slack > required_slack_to_wait:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        """Required method for evaluator instantiation."""
        args, _ = parser.parse_known_args()
        return cls(args)