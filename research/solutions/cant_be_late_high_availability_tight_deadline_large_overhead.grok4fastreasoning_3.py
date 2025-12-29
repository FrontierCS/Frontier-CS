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
        done = sum(self.task_done_time)
        remaining_work = max(0, self.task_duration - done)
        if remaining_work == 0:
            return ClusterType.NONE
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        if remaining_time <= 0:
            return ClusterType.NONE
        gap = self.env.gap_seconds
        buffer = self.restart_overhead
        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                if remaining_time >= remaining_work + buffer:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                return ClusterType.SPOT
        else:
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            else:
                if remaining_time - gap >= remaining_work + buffer:
                    return ClusterType.NONE
                else:
                    return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):  # REQUIRED: For evaluator instantiation
        args, _ = parser.parse_known_args()
        return cls(args)