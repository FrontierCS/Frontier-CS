from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "streak_buffer_strategy"

    def solve(self, spec_path: str) -> "Solution":
        self.pending_spot_streak = 0
        self.min_streak = None
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done = sum(self.task_done_time)
        remaining_work = self.task_duration - done
        remaining_time = self.deadline - self.env.elapsed_seconds

        if remaining_work <= 0:
            return ClusterType.NONE

        if remaining_time <= remaining_work:
            return ClusterType.ON_DEMAND

        buffer = remaining_time - remaining_work
        safe_buffer = self.restart_overhead * 5
        if buffer < safe_buffer:
            return ClusterType.ON_DEMAND

        # Safe to consider spot
        if self.min_streak is None:
            overhead_steps = (self.restart_overhead // self.env.gap_seconds) + 1
            self.min_streak = max(1, overhead_steps)

        if last_cluster_type == ClusterType.SPOT:
            if has_spot:
                self.pending_spot_streak = 0
                return ClusterType.SPOT
            else:
                self.pending_spot_streak = 0
                return ClusterType.ON_DEMAND
        else:
            if has_spot:
                self.pending_spot_streak += 1
                if self.pending_spot_streak >= self.min_streak:
                    self.pending_spot_streak = 0
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                self.pending_spot_streak = 0
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
