from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        # Initialize cache for memoizing work done calculation to improve performance.
        self._work_done_cache: float = 0.0
        self._task_done_len: int = 0
        return self

    def _get_work_done(self) -> float:
        """
        Calculates and memoizes the total work done.
        This avoids re-calculating the sum over the task_done_time list at every step.
        """
        if len(self.task_done_time) > self._task_done_len:
            self._work_done_cache = sum(end - start for start, end in self.task_done_time)
            self._task_done_len = len(self.task_done_time)
        return self._work_done_cache

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.

        The core of this strategy is to calculate a "point of no return"—the latest
        moment one must switch to a reliable On-Demand instance to guarantee
        finishing by the deadline.

        1.  Calculate remaining work and total time needed to finish on On-Demand
            from the current moment. This includes pending restart overheads.
        2.  A safety buffer, equal to one restart overhead, is added to this
            time. This makes the strategy resilient to one future, unexpected
            preemption.
        3.  If the buffered time needed exceeds the time remaining until the deadline,
            we have no more slack and must use On-Demand.
        4.  If there is slack, we prioritize the cheapest options: SPOT if available,
            otherwise NONE (wait), to maximize cost savings. Waiting consumes the
            slack, naturally moving the state towards the point of no return.
        """
        work_done = self._get_work_done()
        work_remaining = self.task_duration - work_done

        # If the job is complete, do nothing. Use a small epsilon for float comparison.
        if work_remaining <= 1e-9:
            return ClusterType.NONE

        # Calculate the time required to finish the rest of the job on On-Demand.
        current_overhead = self.env.remaining_restart_overhead
        time_needed_on_od = current_overhead + work_remaining
        
        # Add a safety buffer to be resilient to a future preemption. A buffer
        # equal to one restart overhead is a reasonable choice.
        safety_buffer = self.restart_overhead
        
        # Calculate the time left until the deadline.
        time_left_to_deadline = self.deadline - self.env.elapsed_seconds

        # Decision point: If the time needed (with buffer) is more than the time
        # left, we are in the critical zone and must use On-Demand.
        if time_needed_on_od + safety_buffer >= time_left_to_deadline:
            return ClusterType.ON_DEMAND
        else:
            # We have slack time. Be greedy to save costs.
            if has_spot:
                # Use the cheapest option.
                return ClusterType.SPOT
            else:
                # Spot is not available; wait for it to become available.
                # This uses up our slack, which is the intended behavior.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):  # REQUIRED: For evaluator instantiation
        args, _ = parser.parse_known_args()
        return cls(args)