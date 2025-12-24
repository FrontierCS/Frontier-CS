from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "smart_scheduler"

    def solve(self, spec_path: str) -> "Solution":
        self.spot_count = 0
        self.total_steps = 0
        self.initial_p = 0.6
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        total_done = sum(self.task_done_time)
        remaining_work = self.task_duration - total_done
        time_left = self.deadline - self.env.elapsed_seconds
        gap = self.env.gap_seconds

        self.total_steps += 1

        if remaining_work <= 0:
            return ClusterType.NONE

        if has_spot:
            self.spot_count += 1
            return ClusterType.SPOT
        else:
            time_left_after = time_left - gap
            if time_left_after <= 0:
                return ClusterType.ON_DEMAND

            if self.total_steps == 1:
                estimated_p = self.initial_p
            else:
                estimated_p = self.spot_count / (self.total_steps - 1)

            required_p = remaining_work / time_left_after if time_left_after > 0 else float('inf')

            if estimated_p >= required_p:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
