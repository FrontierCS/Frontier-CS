import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"  # REQUIRED: unique identifier

    def __init__(self, args):
        super().__init__(args)
        self._initialized = False
        self.THRESHOLD_OD = 0.0
        self.THRESHOLD_WAIT_FOR_SPOT = 0.0

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        return self

    def _initialize_constants(self):
        """
        Lazy initializer for strategy constants.
        This is called on the first step to ensure environment attributes
        like `self.deadline` are available.
        """
        self.THRESHOLD_OD = self.restart_overhead

        initial_slack = self.deadline - self.task_duration
        # Heuristic: Partition the initial slack. We are willing to "spend"
        # half of it on waiting for spot instances (using NONE). The other half
        # is reserved as a buffer for preemptions and mandatory on-demand usage.
        self.THRESHOLD_WAIT_FOR_SPOT = initial_slack / 2.0

        self._initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.

        Args:
            last_cluster_type: The cluster type used in the previous step
            has_spot: Whether spot instances are available this step

        Returns:
            ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        if not self._initialized:
            self._initialize_constants()

        # 1. Calculate remaining work.
        if not self.task_done_time:
            work_done = 0.0
        else:
            work_done = sum(end - start for start, end in self.task_done_time)

        work_rem = self.task_duration - work_done

        # If the job is finished, do nothing to save costs.
        if work_rem <= 1e-9:
            return ClusterType.NONE

        # 2. Calculate the time cushion.
        # The cushion represents the available slack if we were to complete the
        # rest of the job using a guaranteed on-demand instance.
        #   cushion = time_remaining_to_deadline - work_remaining_on_demand
        time_available = self.deadline - self.env.elapsed_seconds
        cushion = time_available - work_rem

        # 3. Decision logic based on the cushion.
        # The strategy uses two thresholds on the cushion to decide the action.

        # If cushion is critically low (less than a potential restart overhead),
        # we must use On-Demand to guarantee finishing on time. A single spot
        # preemption at this stage would cause us to miss the deadline.
        if cushion <= self.THRESHOLD_OD:
            return ClusterType.ON_DEMAND

        # If spot is available and we are not in the critical zone, always use it
        # as it's the most cost-effective way to make progress.
        if has_spot:
            return ClusterType.SPOT

        # If spot is not available, the choice is between ON_DEMAND (costly,
        # but preserves cushion) and NONE (free, but spends cushion).
        if cushion <= self.THRESHOLD_WAIT_FOR_SPOT:
            # The cushion is getting low. We can't afford to wait for spot.
            # Use On-Demand to make progress and preserve our remaining cushion.
            return ClusterType.ON_DEMAND
        else:
            # We have a healthy cushion. We can afford to wait for cheaper
            # spot instances to become available, saving costs by using NONE.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):  # REQUIRED: For evaluator instantiation
        args, _ = parser.parse_known_args()
        return cls(args)