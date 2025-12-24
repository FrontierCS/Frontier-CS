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
        total_done = sum(self.task_done_time)
        remaining_work = self.task_duration - total_done
        remaining_wall = self.deadline - self.env.elapsed_seconds
        if remaining_work <= 0 or remaining_wall <= 0:
            return ClusterType.NONE
        slack = remaining_wall - remaining_work
        oh = self.restart_overhead

        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND  # continue OD, safe

        if last_cluster_type == ClusterType.SPOT and has_spot:
            # can continue SPOT without new overhead
            if slack > oh:
                return ClusterType.SPOT  # safe to continue
            else:
                # risky to continue, try switch to OD if possible
                if slack > oh:
                    return ClusterType.ON_DEMAND  # pay oh now, safe
                else:
                    return ClusterType.SPOT  # have to risk continuing

        # not continuing SPOT: decide to start new SPOT or OD
        # starting new incurs oh now
        if has_spot and slack > 2 * oh:
            return ClusterType.SPOT  # start new SPOT, enough slack for potential extra oh
        else:
            return ClusterType.ON_DEMAND  # use OD (incurs oh if new, but safe after)

    @classmethod
    def _from_args(cls, parser):  # REQUIRED: For evaluator instantiation
        args, _ = parser.parse_known_args()
        return cls(args)
