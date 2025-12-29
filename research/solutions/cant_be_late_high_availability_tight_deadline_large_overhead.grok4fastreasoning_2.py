from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.overhead_timer = 0.0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done = sum(self.task_done_time)
        remaining_work = max(0.0, self.task_duration - done)
        if remaining_work <= 0:
            return ClusterType.NONE
        self.overhead_timer = max(0.0, self.overhead_timer - self.env.gap_seconds)
        preempted = (last_cluster_type == ClusterType.SPOT and not has_spot)
        if preempted:
            self.overhead_timer = self.restart_overhead
        if self.overhead_timer > 0:
            return ClusterType.NONE
        progress = min(self.env.gap_seconds, remaining_work)
        new_rw = remaining_work - progress
        new_elapsed = self.env.elapsed_seconds + self.env.gap_seconds
        safe_for_spot = (new_rw <= 0) or (self.deadline - new_elapsed - self.restart_overhead >= new_rw)
        if has_spot and safe_for_spot:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)