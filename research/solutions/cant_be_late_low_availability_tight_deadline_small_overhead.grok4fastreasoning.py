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
        self.total_done = 0.0
        self.last_len = 0
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
        # Update total_done efficiently
        current_len = len(self.task_done_time)
        if current_len > self.last_len:
            self.total_done += sum(self.task_done_time[self.last_len:])
            self.last_len = current_len

        remaining = self.task_duration - self.total_done
        time_left = self.deadline - self.env.elapsed_seconds

        if remaining <= 0:
            return ClusterType.NONE

        if has_spot and time_left > remaining + self.restart_overhead:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):  # REQUIRED: For evaluator instantiation
        args, _ = parser.parse_known_args()
        return cls(args)