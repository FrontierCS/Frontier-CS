from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        # A factor to determine the caution threshold. We enter "caution mode"
        # when the slack is less than this factor times the restart overhead.
        # This buffer should be able to absorb a few unlucky preemptions.
        caution_factor = 5.0
        self.caution_slack_threshold = caution_factor * self.restart_overhead

        # A factor to determine the panic threshold. We enter "panic mode"
        # when the slack is less than this factor times the restart overhead.
        # At this point, any further time loss is critical.
        panic_factor = 1.0
        self.panic_slack_threshold = panic_factor * self.restart_overhead

        # Cache for calculating total work done efficiently
        self.cached_work_done = 0.0
        self.cached_len_task_done_time = 0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.

        Args:
            last_cluster_type: The cluster type used in the previous step
            has_spot: Whether spot instances are available this step

        Returns:
            ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Incrementally update the total work done for efficiency.
        # This assumes self.task_done_time is an append-only list.
        if len(self.task_done_time) > self.cached_len_task_done_time:
            new_segments = self.task_done_time[self.cached_len_task_done_time:]
            self.cached_work_done += sum(end - start for start, end in new_segments)
            self.cached_len_task_done_time = len(self.task_done_time)

        work_remaining = self.task_duration - self.cached_work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        wall_time_remaining = self.deadline - self.env.elapsed_seconds
        
        # Slack is the time buffer we have if we were to complete the rest of the
        # job using only on-demand instances.
        slack = wall_time_remaining - work_remaining

        # --- Three-Zone Decision Logic ---

        # 1. Panic Zone: Slack is critically low.
        # We must use the guaranteed on-demand option to make progress.
        if slack <= self.panic_slack_threshold:
            return ClusterType.ON_DEMAND

        # If spot instances are available and we are not in panic mode,
        # it is always the optimal choice. It is cheaper than on-demand and
        # makes progress, thus preserving slack (barring preemptions which
        # our slack buffer is designed to handle).
        if has_spot:
            return ClusterType.SPOT

        # At this point, spot is not available. The choice is between waiting
        # (NONE) or using on-demand to make progress.

        # 2. Caution Zone: Slack is positive but below our comfort level.
        # We cannot afford to wait and burn through our remaining slack.
        # We choose to pay for on-demand to preserve the slack we have left.
        if slack <= self.caution_slack_threshold:
            return ClusterType.ON_DEMAND

        # 3. Safe Zone: We have ample slack.
        # We can afford to wait for the cheaper spot instances to become
        # available. Waiting costs nothing but consumes slack, which is an
        # acceptable trade-off when we have a large buffer.
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):  # REQUIRED: For evaluator instantiation
        args, _ = parser.parse_known_args()
        return cls(args)
