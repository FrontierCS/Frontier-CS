import numpy as np
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__()
        self.args = args
        self.spot_price = 0.97
        self.od_price = 3.06
        self.ratio = self.od_price / self.spot_price
        self.restart_overhead_seconds = None
        self.task_duration = None
        self.deadline = None
        self.safety_buffer = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self.restart_overhead_seconds is None:
            self.restart_overhead_seconds = self.restart_overhead
            self.task_duration = self.task_duration
            self.deadline = self.deadline
            self.safety_buffer = min(3600, (self.deadline - self.task_duration) * 0.5)

        if not has_spot:
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.NONE
            elif last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE

        time_used = self.env.elapsed_seconds
        time_left = self.deadline - time_used
        work_done = sum(self.task_done_time) if self.task_done_time else 0
        work_left = self.task_duration - work_done

        effective_time_needed = work_left
        if last_cluster_type == ClusterType.NONE and work_left > 0:
            effective_time_needed += self.restart_overhead_seconds

        if effective_time_needed > time_left - self.safety_buffer:
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.SPOT:
            return ClusterType.SPOT

        spot_expected_savings = self.ratio - 1
        risk_adjusted_savings = spot_expected_savings * (1 - (effective_time_needed / time_left))

        if risk_adjusted_savings > 0.5:
            return ClusterType.SPOT
        elif time_left - effective_time_needed > self.restart_overhead_seconds * 2:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)