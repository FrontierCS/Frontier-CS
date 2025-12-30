from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.state = 'initial'
        self.wait_start = None
        self.wait_threshold = 7200.0  # 2 hours in seconds
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        remaining = self.task_duration - done
        if remaining <= 0:
            return ClusterType.NONE
        time_left = self.deadline - elapsed
        slack = time_left - remaining
        overhead = self.restart_overhead
        tight = slack < overhead

        if self.state == 'initial':
            if tight or not has_spot:
                self.state = 'ondemand'
                return ClusterType.ON_DEMAND
            else:
                self.state = 'spot'
                return ClusterType.SPOT
        elif self.state == 'spot':
            if has_spot:
                return ClusterType.SPOT
            else:
                self.state = 'waiting'
                self.wait_start = elapsed
                if tight:
                    self.state = 'ondemand'
                    return ClusterType.ON_DEMAND
                else:
                    return ClusterType.NONE
        elif self.state == 'waiting':
            waited = elapsed - self.wait_start
            if has_spot:
                self.state = 'spot'
                return ClusterType.SPOT
            else:
                if tight or waited > self.wait_threshold:
                    self.state = 'ondemand'
                    return ClusterType.ON_DEMAND
                else:
                    return ClusterType.NONE
        elif self.state == 'ondemand':
            if has_spot and not tight and slack > 3 * overhead:
                self.state = 'spot'
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        # fallback
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)