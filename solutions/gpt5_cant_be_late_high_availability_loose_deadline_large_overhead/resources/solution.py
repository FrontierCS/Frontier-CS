import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_wait_lock_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self.wait_overhead_multiplier = getattr(args, "wait_overhead_multiplier", 4.0)
        self.wait_margin_hours = getattr(args, "wait_margin_hours", 0.5)
        self.endgame_overhead_multiplier = getattr(args, "endgame_overhead_multiplier", 2.0)
        self.endgame_margin_hours = getattr(args, "endgame_margin_hours", 1.0)
        self.lock_to_on_demand = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work(self) -> float:
        try:
            done = float(sum(self.task_done_time)) if self.task_done_time else 0.0
        except Exception:
            try:
                done = float(self.task_done_time)
            except Exception:
                done = 0.0
        rem = float(self.task_duration) - done
        return rem if rem > 0.0 else 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_time = float(self.env.elapsed_seconds)
        deadline = float(self.deadline)
        remaining_work = self._remaining_work()
        time_left = max(0.0, deadline - current_time)

        if remaining_work <= 0.0:
            return ClusterType.NONE

        restart_overhead = float(self.restart_overhead)
        wait_buffer = restart_overhead * float(self.wait_overhead_multiplier) + self.wait_margin_hours * 3600.0
        endgame_buffer = restart_overhead * float(self.endgame_overhead_multiplier) + self.endgame_margin_hours * 3600.0

        if not self.lock_to_on_demand and time_left <= remaining_work + endgame_buffer:
            self.lock_to_on_demand = True

        if self.lock_to_on_demand:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        slack = time_left - remaining_work
        if slack > wait_buffer:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
