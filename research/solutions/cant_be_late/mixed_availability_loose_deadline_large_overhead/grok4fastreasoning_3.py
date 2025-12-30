from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.od_mode = False
        self.started = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done = sum(self.task_done_time)
        remaining = self.task_duration - done
        time_left = self.deadline - self.env.elapsed_seconds
        overhead = self.restart_overhead
        gap = self.env.gap_seconds

        if remaining <= 0:
            return ClusterType.NONE

        # Conservative check for tight time
        if time_left <= remaining + 2 * overhead:
            self.od_mode = True
            return ClusterType.ON_DEMAND

        if not self.started:
            self.started = True
            if has_spot:
                return ClusterType.SPOT
            else:
                self.od_mode = True
                return ClusterType.ON_DEMAND

        if self.od_mode or last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.SPOT:
            if has_spot:
                return ClusterType.SPOT
            else:
                self.od_mode = True
                return ClusterType.ON_DEMAND

        # last_cluster_type == ClusterType.NONE (during overhead or pause)
        self.od_mode = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)