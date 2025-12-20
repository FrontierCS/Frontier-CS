import collections
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    A strategy that balances cost and completion risk by maintaining a time buffer.

    The core idea is to maintain a "slack" time, defined as the time remaining
    until the deadline minus the time required to complete the rest of the job on
    On-Demand instances.

    - If this slack falls below a critical buffer (CRITICAL_BUFFER_SECONDS),
      it switches to On-Demand to guarantee completion.
    - Otherwise, it prefers using Spot instances for their low cost.
    - If Spot is unavailable, it decides whether to wait (NONE) or use On-Demand
      based on the recent historical availability of Spot instances. A moving
      average of availability is used to adapt to long outages.
    """
    NAME = "expert_programmer_solution"

    # A safety buffer. If slack falls below this, always use On-Demand.
    CRITICAL_BUFFER_SECONDS: int = 2 * 3600  # 2 hours
    # Window size for calculating moving average of spot availability (in steps).
    AVAILABILITY_WINDOW_SIZE: int = 20
    # If recent spot availability is below this threshold, use On-Demand instead of waiting.
    AVAILABILITY_THRESHOLD: float = 0.25

    def solve(self, spec_path: str) -> "Solution":
        """Initializes the strategy's state before the simulation begins."""
        self.availability_history = collections.deque(
            [True] * self.AVAILABILITY_WINDOW_SIZE,
            maxlen=self.AVAILABILITY_WINDOW_SIZE
        )
        self._work_done_cache: float = 0.0
        self._last_task_done_len: int = 0
        return self

    def _get_work_done_cached(self) -> float:
        """
        Returns the total work done, using a cache to avoid re-computing the sum
        at every step.
        """
        if len(self.task_done_time) > self._last_task_done_len:
            self._work_done_cache = sum(end - start for start, end in self.task_done_time)
            self._last_task_done_len = len(self.task_done_time)
        return self._work_done_cache

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """Makes a decision at each time step on which cluster type to use."""
        self.availability_history.append(has_spot)

        work_done = self._get_work_done_cached()
        work_rem = self.task_duration - work_done
        
        if work_rem <= 0:
            return ClusterType.NONE

        time_rem_until_deadline = self.deadline - self.env.elapsed_seconds

        # This is the time required to finish if we only use On-Demand from now on,
        # plus a safety buffer.
        critical_time_needed = work_rem + self.CRITICAL_BUFFER_SECONDS
        
        # If remaining time is less than this critical value, we must use On-Demand.
        if time_rem_until_deadline <= critical_time_needed:
            return ClusterType.ON_DEMAND

        # If we have enough slack, we can be opportunistic.
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot is not available. Decide based on recent availability.
            # Using sum() on a deque of booleans is efficient.
            recent_availability = sum(self.availability_history) / self.AVAILABILITY_WINDOW_SIZE

            if recent_availability < self.AVAILABILITY_THRESHOLD:
                # Outlook is poor, don't waste slack waiting.
                return ClusterType.ON_DEMAND
            else:
                # Outlook is good, wait for Spot to return.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """Required classmethod for evaluator instantiation."""
        args, _ = parser.parse_known_args()
        return cls(args)
