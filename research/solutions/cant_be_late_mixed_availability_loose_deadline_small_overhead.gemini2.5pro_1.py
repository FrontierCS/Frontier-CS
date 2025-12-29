import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args: argparse.Namespace):
        super().__init__(args)
        self.urgent_time_factor: float = getattr(args, 'urgent_time_factor', 1.25)
        self.critical_slack_buffer: float = getattr(args, 'critical_slack_buffer', 180.0)
        self.last_work_done: float = 0.0
        self.pending_overhead: float = 0.0

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser) -> "Solution":
        parser.add_argument('--urgent_time_factor', type=float, default=1.25)
        parser.add_argument('--critical_slack_buffer', type=float, default=180.0)
        args, _ = parser.parse_known_args()
        return cls(args)

    def solve(self, spec_path: str) -> "Solution":
        self.last_work_done = 0.0
        self.pending_overhead = 0.0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_work_done = sum(end - start for start, end in self.task_done_time)
        progress_this_step = current_work_done - self.last_work_done

        time_spent_working = 0
        if last_cluster_type in [ClusterType.SPOT, ClusterType.ON_DEMAND]:
            time_spent_working = self.env.gap_seconds

        if time_spent_working > 0:
            overhead_paid = max(0, time_spent_working - progress_this_step)
            self.pending_overhead = max(0, self.pending_overhead - overhead_paid)

        if last_cluster_type == ClusterType.SPOT and self.env.cluster_type == ClusterType.NONE:
            self.pending_overhead = self.restart_overhead

        base_work_remaining = self.task_duration - current_work_done
        effective_work_remaining = base_work_remaining + self.pending_overhead
        time_to_deadline = self.deadline - self.env.elapsed_seconds

        decision: ClusterType

        if time_to_deadline <= effective_work_remaining + self.critical_slack_buffer:
            decision = ClusterType.ON_DEMAND
        elif time_to_deadline <= effective_work_remaining * self.urgent_time_factor:
            if has_spot:
                decision = ClusterType.SPOT
            else:
                decision = ClusterType.ON_DEMAND
        else:
            if has_spot:
                decision = ClusterType.SPOT
            else:
                decision = ClusterType.NONE

        self.last_work_done = current_work_done
        return decision