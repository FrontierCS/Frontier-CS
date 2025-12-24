from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.num_periods = 0
        self.total_period_length = 0
        self.current_spot_run = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE
        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0:
            return ClusterType.NONE
        required_rate = remaining_work / time_left if time_left > 0 else float('inf')
        if required_rate > 1.0:
            return ClusterType.ON_DEMAND

        # Update spot run length
        was_spot = last_cluster_type == ClusterType.SPOT
        if has_spot:
            if was_spot:
                self.current_spot_run += 1
            else:
                self.current_spot_run = 1
        else:
            if was_spot:
                # Preemption, end of period
                self.total_period_length += self.current_spot_run
                self.num_periods += 1
                self.current_spot_run = 0

        # Decide
        if has_spot and last_cluster_type == ClusterType.SPOT:
            # Continue current spot run
            return ClusterType.SPOT
        elif has_spot:
            # Decide whether to start a new spot run
            if self.num_periods > 0:
                avg_period_steps = self.total_period_length / self.num_periods
                avg_period_time = avg_period_steps * self.env.gap_seconds
            else:
                avg_period_time = float('inf')
            if avg_period_time > 2 * self.restart_overhead:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
