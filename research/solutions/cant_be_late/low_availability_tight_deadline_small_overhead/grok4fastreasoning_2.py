from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType
import sum

class Solution(Strategy):
    NAME = "streak_aware_solution"

    def __init__(self, args):
        super().__init__(args)
        self.spot_streak = 0
        self.using_spot = False
        self.min_streak = None

    def solve(self, spec_path: str) -> "Solution":
        self.spot_streak = 0
        self.using_spot = False
        self.min_streak = None
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        OD_PRICE_HR = 3.06
        SPOT_PRICE_HR = 0.97
        DELTA_HR = OD_PRICE_HR - SPOT_PRICE_HR
        h_hr = self.restart_overhead / 3600.0
        break_even_extra_hr = h_hr * OD_PRICE_HR / DELTA_HR
        if self.min_streak is None:
            wait_steps = int(break_even_extra_hr * 3600 / self.env.gap_seconds) + 1
            self.min_streak = max(3, wait_steps)

        done = sum(self.task_done_time)
        remaining_work = max(0.0, self.task_duration - done)
        if remaining_work <= 0:
            return ClusterType.NONE

        remaining_time = self.deadline - self.env.elapsed_seconds + self.env.gap_seconds
        slack = remaining_time - remaining_work
        buffer = self.restart_overhead * 2
        if slack < buffer:
            self.using_spot = False
            self.spot_streak = 0
            return ClusterType.ON_DEMAND

        if has_spot:
            self.spot_streak += 1
        else:
            self.spot_streak = 0

        if self.using_spot:
            if has_spot:
                return ClusterType.SPOT
            else:
                self.using_spot = False
                return ClusterType.ON_DEMAND
        else:
            if not has_spot:
                return ClusterType.ON_DEMAND
            else:
                if self.spot_streak >= self.min_streak:
                    self.using_spot = True
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)