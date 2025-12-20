import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    CRITICAL_SLACK_SECONDS = 180.0 + 10.0
    COMFORTABLE_SLACK_SECONDS = 2.0 * 3600.0

    def solve(self, spec_path: str) -> "Solution":
        self.last_work_done: float = 0.0
        self.pending_overhead: float = 0.0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_work_done = sum(self.task_done_time)
        progress = current_work_done - self.last_work_done

        is_preempted = (last_cluster_type == ClusterType.SPOT and
                        progress < self.env.gap_seconds * 0.1)

        if is_preempted:
            self.pending_overhead = self.restart_overhead
        elif progress > 0:
            self.pending_overhead = max(0.0, self.pending_overhead - progress)

        base_work_remaining = self.task_duration - current_work_done
        effective_work_remaining = base_work_remaining + self.pending_overhead

        time_left_to_deadline = self.deadline - self.env.elapsed_seconds

        slack = time_left_to_deadline - effective_work_remaining

        decision: ClusterType

        if slack <= self.CRITICAL_SLACK_SECONDS:
            decision = ClusterType.ON_DEMAND
        else:
            if has_spot:
                decision = ClusterType.SPOT
            else:
                if slack > self.COMFORTABLE_SLACK_SECONDS:
                    decision = ClusterType.NONE
                else:
                    decision = ClusterType.ON_DEMAND

        self.last_work_done = current_work_done

        return decision

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        args, _ = parser.parse_known_args()
        return cls(args)
