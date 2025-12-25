from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.remaining_overhead = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        total_done = sum(self.task_done_time)
        if total_done >= self.task_duration:
            return ClusterType.NONE
        remaining_work = self.task_duration - total_done
        time_left = self.deadline - self.env.elapsed_seconds
        slack = time_left - remaining_work

        if last_cluster_type == ClusterType.SPOT and not has_spot and self.remaining_overhead == 0:
            self.remaining_overhead = self.restart_overhead

        if self.remaining_overhead > 0:
            self.remaining_overhead -= self.env.gap_seconds
            if self.remaining_overhead < 0:
                self.remaining_overhead = 0

        in_overhead = self.remaining_overhead > 0

        safety_buffer = self.restart_overhead * 10
        use_od_for_safety = slack <= safety_buffer

        if in_overhead:
            if has_spot:
                self.remaining_overhead = 0
                return ClusterType.SPOT
            else:
                wait_threshold = self.restart_overhead * 5
                if slack > wait_threshold:
                    return ClusterType.NONE
                else:
                    self.remaining_overhead = 0
                    return ClusterType.ON_DEMAND
        else:
            if total_done >= self.task_duration:
                return ClusterType.NONE
            if not has_spot or use_od_for_safety:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)