import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        # This multiplier determines the size of our safety time buffer.
        # A higher value means we are more conservative, switching to On-Demand
        # earlier when Spot is unavailable.
        # Total initial slack is 4h (14400s). Restart overhead is 3m (180s).
        # A multiplier of 40 yields a safety buffer of 40 * 180s = 7200s = 2h.
        # This means we are willing to "spend" up to 2h of our 4h slack
        # waiting for Spot instances to become available.
        self.SAFETY_BUFFER_OVERHEAD_MULTIPLIER = 40

        # State variables to be initialized in solve()
        self.safety_buffer_seconds = None
        self.work_done_cached = 0.0
        self.processed_segments_count = 0

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the strategy based on the problem specification.
        """
        self.safety_buffer_seconds = self.SAFETY_BUFFER_OVERHEAD_MULTIPLIER * self.restart_overhead
        self.work_done_cached = 0.0
        self.processed_segments_count = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decision logic for each time step.
        """
        # Incrementally update the cached value of total work done for efficiency.
        if len(self.task_done_time) > self.processed_segments_count:
            for i in range(self.processed_segments_count, len(self.task_done_time)):
                start, end = self.task_done_time[i]
                self.work_done_cached += (end - start)
            self.processed_segments_count = len(self.task_done_time)

        work_remaining = self.task_duration - self.work_done_cached

        # If the task is finished, do nothing.
        if work_remaining <= 0:
            return ClusterType.NONE

        # Always use Spot instances if they are available, as it's the
        # most cost-effective way to make progress.
        if has_spot:
            return ClusterType.SPOT

        # If Spot is not available, decide between waiting (NONE) or using
        # a guaranteed On-Demand instance.
        
        # Calculate the current time slack:
        # Slack = (Time left until deadline) - (Time needed to finish on On-Demand)
        time_until_deadline = self.deadline - self.env.elapsed_seconds
        current_slack_seconds = time_until_deadline - work_remaining

        # Compare current slack to our pre-defined safety buffer.
        if current_slack_seconds > self.safety_buffer_seconds:
            # We have more slack than our safety buffer. We can afford to wait
            # for Spot to become available again to save costs.
            return ClusterType.NONE
        else:
            # Our time slack has fallen below the safety threshold. It's too
            # risky to wait. We must use an On-Demand instance to guarantee
            # progress and avoid missing the deadline.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        """
        Required classmethod for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)