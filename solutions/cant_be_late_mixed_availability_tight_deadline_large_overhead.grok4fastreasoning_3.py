from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.in_safe_mode = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        total_done = sum(self.task_done_time)
        remaining = self.task_duration - total_done
        if remaining <= 0:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        if elapsed == 0:
            past_speed = 1.0
        else:
            past_speed = total_done / elapsed

        time_left = self.deadline - elapsed
        if time_left <= 0:
            return ClusterType.NONE

        projected_remaining_time = remaining / past_speed if past_speed > 0 else float('inf')
        projected_finish = elapsed + projected_remaining_time

        if projected_finish > self.deadline:
            self.in_safe_mode = True

        if self.in_safe_mode:
            return ClusterType.ON_DEMAND
        elif has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
