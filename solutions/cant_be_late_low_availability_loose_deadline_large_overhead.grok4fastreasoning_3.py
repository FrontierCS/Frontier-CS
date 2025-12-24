from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.num_steps = 0
        self.num_spot_avail = 0
        self.observed_p = 0.0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining_work = self.task_duration - sum(self.task_done_time)
        time_left = self.deadline - self.env.elapsed_seconds
        if remaining_work <= 0 or time_left <= 0:
            return ClusterType.NONE
        slack = time_left - remaining_work
        if slack < 0:
            return ClusterType.ON_DEMAND
        p_est = self.observed_p
        if self.num_steps == 0:
            p_est = 0.2
        denom = max(1 - p_est, 0.01)
        buffer = self.restart_overhead * 5
        effective_slack = max(slack - buffer, 0)
        target_remaining = (p_est / denom) * effective_slack
        if remaining_work <= target_remaining:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE
        else:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        # Update observed
        self.num_steps += 1
        if has_spot:
            self.num_spot_avail += 1
        self.observed_p = self.num_spot_avail / self.num_steps if self.num_steps > 0 else 0.0

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
