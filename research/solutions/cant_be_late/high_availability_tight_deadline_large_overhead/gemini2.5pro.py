import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    A strategy based on maintaining a "slack buffer".

    Core Idea:
    The total available slack is the time between the deadline and the time required
    to finish the remaining work on a non-stop On-Demand instance.
    This slack is a precious resource that gets consumed by Spot unavailability
    (when we choose to wait) and Spot preemptions (which incur a restart overhead).

    The strategy divides the slack into two conceptual parts:
    1. A "spending" slack: We are willing to use this portion of slack to wait
       for cheap Spot instances to become available.
    2. A "safety buffer": This portion of slack is preserved for handling future
       preemptions and long unavailability periods.

    Decision Logic:
    1.  PANIC MODE: If the current slack is less than the time cost of a single
        preemption (`restart_overhead`), we are at high risk of missing the deadline.
        In this mode, we use On-Demand exclusively to guarantee completion.

    2.  NORMAL MODE:
        - If Spot instances are available, we always use them. This is the most
          cost-effective way to make progress.
        - If Spot is not available, we look at our current slack:
            - If slack > safety buffer: We can afford to wait. We choose NONE,
              saving money and hoping Spot returns soon.
            - If slack <= safety buffer: Our safety margin is getting thin. We must
              make progress. We choose On-Demand to complete work and prevent
              our slack from decreasing further.

    The size of the safety buffer is determined by `SLACK_BUFFER_FACTOR`, a tunable
    parameter. It's set to a value that aims to preserve a significant portion
    of the initial total slack to handle uncertainties throughout the job's duration.
    """
    NAME = "slack_buffer_strategy"

    def solve(self, spec_path: str) -> "Solution":
        self.SLACK_BUFFER_FACTOR = 10.0
        self.slack_buffer_seconds = 0.0
        self._is_initialized = False
        return self

    def _initialize(self):
        """
        Initializes strategy constants on the first `_step` call.
        """
        self.slack_buffer_seconds = self.SLACK_BUFFER_FACTOR * self.restart_overhead
        self._is_initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._is_initialized:
            self._initialize()

        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 1e-9:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_to_deadline = self.deadline - current_time

        if time_to_deadline < work_remaining:
            return ClusterType.ON_DEMAND

        current_slack = time_to_deadline - work_remaining

        if current_slack <= self.restart_overhead:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        else:
            if current_slack > self.slack_buffer_seconds:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)