import collections

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    # --- Hyperparameters ---
    # The moving window size for estimating spot availability.
    HISTORY_SIZE = 240
    # The lower and upper bounds for our dynamic urgency threshold.
    MIN_THRESHOLD = 0.90
    MAX_THRESHOLD = 1.05
    # A neutral prior for spot availability at the start of the simulation.
    PRIOR_AVAILABILITY = 0.5

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy's state before the simulation begins.
        """
        # Initialize a deque with a neutral prior for spot availability.
        num_ones = int(self.HISTORY_SIZE * self.PRIOR_AVAILABILITY)
        num_zeros = self.HISTORY_SIZE - num_ones
        initial_history = [1] * num_ones + [0] * num_zeros
        self.spot_history = collections.deque(initial_history, maxlen=self.HISTORY_SIZE)

        # Pre-calculate the deadline-to-task ratio for urgency calculations.
        if self.task_duration > 0:
            self.deadline_ratio = self.deadline / self.task_duration
        else:
            self.deadline_ratio = float('inf')
        
        # Initialize caches for efficient calculation of work done.
        self.work_done_cache = 0.0
        self.last_task_done_len = 0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        The core decision-making logic, executed at each time step.
        """
        # Efficiently update the total work done using a cache.
        if len(self.task_done_time) > self.last_task_done_len:
            new_segments = self.task_done_time[self.last_task_done_len:]
            self.work_done_cache += sum(end - start for start, end in new_segments)
            self.last_task_done_len = len(self.task_done_time)
        
        work_remaining = self.task_duration - self.work_done_cache
        
        # If the task is finished, do nothing to minimize cost.
        if work_remaining <= 0:
            return ClusterType.NONE

        # Update the spot availability history.
        self.spot_history.append(1 if has_spot else 0)

        t_now = self.env.elapsed_seconds
        time_left = self.deadline - t_now

        # --- Decision Logic ---

        # 1. Panic Mode: A safety net to prevent missing the deadline.
        # If the time required to finish on On-Demand exceeds the time left,
        # we must use any available compute resource.
        if work_remaining >= time_left - self.env.gap_seconds:
            return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND

        # 2. Normal Operation: Spot is always preferred when available.
        if has_spot:
            return ClusterType.SPOT

        # 3. Adaptive Decision: Spot is unavailable. Choose between On-Demand and None.
        
        # Estimate the current spot market's reliability.
        avg_availability = sum(self.spot_history) / len(self.spot_history)

        # Calculate a dynamic threshold based on spot reliability.
        # In good markets (high availability), be more patient (higher threshold).
        # In bad markets (low availability), be more aggressive (lower threshold).
        dynamic_threshold = self.MIN_THRESHOLD + \
            (self.MAX_THRESHOLD - self.MIN_THRESHOLD) * avg_availability
        
        # Avoid division by zero if we are past the deadline.
        if time_left <= 0:
             return ClusterType.ON_DEMAND
        
        # Calculate the urgency ratio, which measures how far behind or ahead
        # of a pro-rata schedule we are.
        urgency_ratio = (work_remaining * self.deadline_ratio) / time_left

        if urgency_ratio > dynamic_threshold:
            # We are behind our adaptive schedule; use On-Demand to catch up.
            return ClusterType.ON_DEMAND
        else:
            # We are ahead of schedule; we can afford to wait for a Spot instance.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        Required classmethod for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
