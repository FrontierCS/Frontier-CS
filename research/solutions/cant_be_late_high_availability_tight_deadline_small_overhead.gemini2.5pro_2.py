import argparse
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
        self.total_work_done = 0.0
        self.last_task_done_time_len = 0
        self.spot_down_since = None

        self.CRITICAL_BUFFER_FACTOR = 3.0
        self.WAIT_TIME_PER_HOUR_OF_BUFFER = 90.0
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
        if len(self.task_done_time) > self.last_task_done_time_len:
            new_entries = self.task_done_time[self.last_task_done_time_len:]
            for start, end in new_entries:
                self.total_work_done += (end - start)
            self.last_task_done_time_len = len(self.task_done_time)

        work_remaining = self.task_duration - self.total_work_done
        if work_remaining <= 1e-9:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        safety_buffer = time_to_deadline - work_remaining

        if safety_buffer < 0:
            return ClusterType.NONE

        critical_buffer = self.CRITICAL_BUFFER_FACTOR * self.restart_overhead
        if safety_buffer <= critical_buffer:
            return ClusterType.ON_DEMAND

        if has_spot:
            self.spot_down_since = None
            return ClusterType.SPOT

        if self.spot_down_since is None:
            self.spot_down_since = self.env.elapsed_seconds

        spot_downtime = self.env.elapsed_seconds - self.spot_down_since

        max_wait_time = (safety_buffer / 3600.0) * self.WAIT_TIME_PER_HOUR_OF_BUFFER

        if spot_downtime > max_wait_time:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):  # REQUIRED: For evaluator instantiation
        args, _ = parser.parse_known_args()
        return cls(args)