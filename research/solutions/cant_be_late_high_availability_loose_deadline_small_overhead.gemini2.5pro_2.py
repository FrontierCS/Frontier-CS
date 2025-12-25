import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    An adaptive strategy for the Cant-Be-Late Scheduling Problem.

    This strategy makes decisions based on a "pressure" metric, defined as the
    ratio of remaining work to the time left until the deadline. This represents
    the average progress rate required to finish on time.

    The core idea is to compare this required rate against the expected progress
    rate of a cost-effective (spot-centric) strategy. The expected rate is
    estimated by observing the historical availability of spot instances.

    - If the required rate ('pressure') is higher than what a spot-centric
      strategy can be expected to deliver, the strategy switches to the more
      reliable but expensive On-Demand instances to ensure progress.
    - If the pressure is low, indicating a comfortable time buffer, the strategy
      aggressively pursues cost savings by using Spot instances when available
      and waiting (cost-free) when they are not.

    The spot availability is learned online, starting with an optimistic initial
    guess and converging to the true observed rate of the specific trace. This
    allows the strategy to adapt to different environments, from high to low
    spot availability. A safety margin is included to make decisions more
    conservative and robust against unfavorable sequences of events like
    preemptions or long spot droughts.
    """
    NAME = "adaptive_pressure_v1"

    def __init__(self, args=None):
        super().__init__()
        self.args = args

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy's state and hyperparameters.
        """
        # --- Hyperparameters ---
        # Initial guess for spot availability. Set slightly above the overall
        # required progress rate (48/70) to encourage using Spot at the start.
        self.INITIAL_P_S_EST = 0.72

        # Number of steps to use the initial guess before switching to the
        # observed availability rate.
        self.BURN_IN_STEPS = 100

        # A buffer to make the strategy more conservative. It will switch to
        # On-Demand even if the required rate is slightly lower than the
        # estimated spot availability.
        self.SAFETY_MARGIN = 0.05

        # --- State Variables ---
        # Counters for learning spot availability online.
        self.total_steps = 0
        self.spot_available_steps = 0
        
        # Caching variables for performance optimization.
        self._work_done_cache = 0.0
        self._last_task_done_len = 0
        
        return self

    def _get_total_work_done(self) -> float:
        """
        Calculates the total work done so far.
        Uses caching to avoid re-calculating the sum over the entire list
        at every step, assuming work segments are only ever appended.
        """
        if len(self.task_done_time) == self._last_task_done_len:
            return self._work_done_cache

        new_segments = self.task_done_time[self._last_task_done_len:]
        self._work_done_cache += sum(end - start for start, end in new_segments)
        self._last_task_done_len = len(self.task_done_time)
        return self._work_done_cache

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decision-making function called at each time step.
        """
        # 1. Update state for online learning
        self.total_steps += 1
        if has_spot:
            self.spot_available_steps += 1

        # 2. Calculate current work and time remaining
        total_work_done = self._get_total_work_done()
        work_remaining = self.task_duration - total_work_done

        # If the job is done, do nothing.
        if work_remaining <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # 3. Handle panic mode
        # If the remaining work is more than the time left, finishing is
        # impossible. Run On-Demand to minimize the failure. This also
        # safely handles the case where time_to_deadline is zero or negative.
        if work_remaining >= time_to_deadline:
            return ClusterType.ON_DEMAND

        # 4. Estimate spot availability
        if self.total_steps < self.BURN_IN_STEPS:
            p_s_est = self.INITIAL_P_S_EST
        else:
            p_s_est = self.spot_available_steps / self.total_steps
        
        # 5. Core decision logic
        # "Pressure" is the required average progress rate from now until the deadline.
        pressure = work_remaining / time_to_deadline
        
        # The decision threshold is our estimate of what a spot-centric strategy
        # can deliver, made more conservative by a safety margin.
        threshold = p_s_est - self.SAFETY_MARGIN

        if pressure > threshold:
            # The situation is tight. The required progress rate is higher than
            # what we can safely expect from a spot-centric strategy.
            # We must use On-Demand to guarantee progress and avoid the risk of
            # preemption or unavailability.
            return ClusterType.ON_DEMAND
        else:
            # We have a comfortable time buffer. We can pursue cost savings.
            # Use Spot if it's available, otherwise wait for it to become available.
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        """
        Required classmethod for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)