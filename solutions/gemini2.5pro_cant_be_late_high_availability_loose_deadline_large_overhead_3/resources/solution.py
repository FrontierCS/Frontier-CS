import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the strategy with hyperparameters.
        """
        # N_BUFFER: Number of future preemptions to budget for in our safety buffer.
        # A larger value makes the strategy more conservative.
        self.N_BUFFER = 7.0

        # P_SPOT_ESTIMATE: Estimated average availability of Spot instances.
        # Used to decide whether to wait for Spot or use On-Demand.
        self.P_SPOT_ESTIMATE = 0.60

        # PROACTIVE_BUFFER_FACTOR: Multiplier for restart_overhead to make
        # the decision to switch from NONE to ON_DEMAND more proactive.
        self.PROACTIVE_BUFFER_FACTOR = 1.0

        # Caching for performance
        self._total_work_done_cache = 0.0
        self._last_task_done_time_len = 0

        return self

    def _get_total_work_done(self) -> float:
        """
        Calculates the total work done, with caching to avoid re-summing a
        potentially long list at every step.
        """
        if len(self.task_done_time) > self._last_task_done_time_len:
            self._total_work_done_cache = sum(
                end - start for start, end in self.task_done_time
            )
            self._last_task_done_time_len = len(self.task_done_time)
        return self._total_work_done_cache

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        The main decision-making logic, called at each time step.
        """
        # 1. Calculate current progress and remaining work.
        total_work_done = self._get_total_work_done()
        work_remaining = self.task_duration - total_work_done

        # If the job is finished, do nothing to save costs.
        if work_remaining <= 0:
            return ClusterType.NONE

        # 2. Calculate time remaining until the deadline.
        elapsed_time = self.env.elapsed_seconds
        time_left = self.deadline - elapsed_time

        # If we've passed the deadline, this is a failure state.
        if time_left <= 0:
            return ClusterType.ON_DEMAND

        # 3. Primary Safety Check: The "Point of No Return".
        # If the time left is less than the work remaining plus a safety buffer
        # for N_BUFFER future preemptions, we must use ON_DEMAND to guarantee completion.
        safety_buffer = self.N_BUFFER * self.restart_overhead
        buffered_work_remaining = work_remaining + safety_buffer

        if buffered_work_remaining >= time_left:
            return ClusterType.ON_DEMAND

        # 4. Main Strategy: If we are not in the danger zone.
        # If Spot is available, it's always the cheapest way to make progress.
        if has_spot:
            return ClusterType.SPOT

        # If Spot is not available, choose between expensive progress (ON_DEMAND)
        # or consuming our time buffer (NONE).
        # We calculate a "required progress rate" to make this decision.
        proactive_buffer = self.PROACTIVE_BUFFER_FACTOR * self.restart_overhead
        proactive_work_remaining = work_remaining + proactive_buffer
        
        required_rate = proactive_work_remaining / time_left

        if required_rate > self.P_SPOT_ESTIMATE:
            # If the rate needed to finish on time is higher than what we expect
            # Spot to provide, we must use ON_DEMAND to avoid falling behind.
            return ClusterType.ON_DEMAND
        else:
            # We have enough slack to wait for Spot to become available again.
            # This is the primary cost-saving action.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        Required classmethod for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
