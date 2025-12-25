from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "cant_be_late"

    def solve(self, spec_path: str) -> "Solution":
        self.committed_overheads = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done = sum(self.task_done_time)
        remaining_work = max(0.0, self.task_duration - done)
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        if remaining_work == 0 or remaining_time <= 0:
            return ClusterType.NONE

        # Detect preemption
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.committed_overheads = max(0, self.committed_overheads - 1)

        # Decide
        safety_overhead = 0.0
        if has_spot and last_cluster_type == ClusterType.SPOT:
            if remaining_time >= remaining_work + self.committed_overheads * self.restart_overhead + safety_overhead:
                choice = ClusterType.SPOT
            else:
                choice = ClusterType.ON_DEMAND
        elif has_spot and remaining_time >= remaining_work + (self.committed_overheads + 1) * self.restart_overhead + safety_overhead:
            choice = ClusterType.SPOT
        else:
            choice = ClusterType.NONE

        # Override to OD if possible
        if choice == ClusterType.NONE and remaining_time >= remaining_work:
            choice = ClusterType.ON_DEMAND

        # Commit if starting new spot
        if choice == ClusterType.SPOT and last_cluster_type != ClusterType.SPOT:
            self.committed_overheads += 1

        return choice

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)