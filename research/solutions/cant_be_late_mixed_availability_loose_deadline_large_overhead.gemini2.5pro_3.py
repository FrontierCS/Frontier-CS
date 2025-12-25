import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.base_safety_margin = 1.1
        self.preemption_rate_factor_margin = 2.0
        self.wait_threshold_factor = 4.0
        self.preemptions = 0
        self.total_spot_steps_chosen = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if last_cluster_type == ClusterType.SPOT:
            self.total_spot_steps_chosen += 1
            if self.env.cluster_type == ClusterType.NONE:
                self.preemptions += 1

        work_done = sum(self.task_done_time)
        work_rem = self.task_duration - work_done

        if work_rem <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds

        if self.total_spot_steps_chosen > 5:
            preemption_rate = self.preemptions / self.total_spot_steps_chosen
        else:
            preemption_rate = 0.0

        safety_margin = self.base_safety_margin + preemption_rate * self.preemption_rate_factor_margin
        
        critical_time_needed = work_rem + self.restart_overhead * safety_margin
        if critical_time_needed >= time_left:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        current_slack = time_left - work_rem
        wait_threshold = self.restart_overhead * self.wait_threshold_factor

        if current_slack > wait_threshold:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        args, _ = parser.parse_known_args()
        return cls(args)