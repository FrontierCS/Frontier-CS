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
        # Your decision logic here
        done = sum(self.task_done_time)
        if done >= self.task_duration:
            return ClusterType.NONE
        remaining_work = self.task_duration - done
        remaining_time = self.deadline - self.env.elapsed_seconds
        if remaining_time <= 0:
            return ClusterType.NONE
        required_rate = remaining_work / remaining_time
        is_urgent = required_rate > 0.85
        if is_urgent:
            return ClusterType.ON_DEMAND
        if has_spot:
            # Do not return SPOT if not has_spot, but here it is
            return ClusterType.SPOT
        else:
            slack = remaining_time - remaining_work
            wait_threshold = 4 * 3600  # 4 hours in seconds
            if slack > wait_threshold:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):  # REQUIRED: For evaluator instantiation
        args, _ = parser.parse_known_args()
        return cls(args)
