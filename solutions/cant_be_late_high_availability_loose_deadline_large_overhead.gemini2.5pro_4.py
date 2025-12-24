from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy by setting a fixed safety buffer.

        This method is called once before the simulation starts. We use it to
        pre-calculate a safety buffer, which is a critical parameter for our
        decision-making logic in the `_step` method.
        """
        # The safety buffer is the minimum amount of slack time we want to
        # maintain. If the projected slack falls below this, we switch to
        # on-demand. A value of 3.5 hours is chosen as a balance between
        # cost-effectiveness and robustness against spot outages or multiple
        # preemptions. Given the total initial slack of 22 hours (70h deadline
        # - 48h task), this buffer represents a reasonable margin for error.
        self.safety_buffer_seconds = 3.5 * 3600.0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Implements the core decision-making logic for each time step.

        The strategy is to use the cheapest resource (Spot) as long as we have
        a comfortable time buffer. If the buffer shrinks to a critical level,
        we switch to the reliable but expensive resource (On-Demand) to
        guarantee completion before the deadline.
        """
        # 1. Calculate the amount of work remaining.
        # self.task_done_time is a list of (start_time, end_time) tuples
        # representing successful work intervals.
        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If the task is already completed, no further resources are needed.
        if work_remaining <= 0:
            return ClusterType.NONE

        # 2. Calculate the effective slack time.
        # This is the total time remaining until the hard deadline.
        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # "Effective slack" is defined as the time buffer we would have left at
        # the deadline if we were to complete all remaining work using only
        # on-demand instances, starting from this moment.
        effective_slack = time_to_deadline - work_remaining

        # 3. Make a decision based on the effective slack.
        if effective_slack <= self.safety_buffer_seconds:
            # If our effective slack has fallen below the pre-defined safety
            # buffer, we are in the "critical zone". To avoid missing the
            # deadline, we must use the guaranteed on-demand instances from
            # this point forward.
            return ClusterType.ON_DEMAND
        else:
            # We have sufficient slack, so we can prioritize minimizing cost.
            if has_spot:
                # Spot instances are available and are the most cost-effective
                # choice.
                return ClusterType.SPOT
            else:
                # Spot instances are not available. Since we have a comfortable
                # time buffer, it is cheaper to wait (do nothing) for spot to
                # become available again, rather than paying the premium for
                # on-demand instances.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        Required classmethod to instantiate the strategy for the evaluator.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
