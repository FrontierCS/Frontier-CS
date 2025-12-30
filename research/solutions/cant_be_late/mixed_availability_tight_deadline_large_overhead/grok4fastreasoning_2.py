from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "cant_be_late_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        if time_left <= 0:
            return ClusterType.NONE
        work_done = self.task_duration - remaining_work
        overheads_so_far = elapsed - work_done
        total_slack = self.deadline - self.task_duration
        remaining_slack = total_slack - overheads_so_far
        if has_spot and remaining_slack >= self.restart_overhead:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)