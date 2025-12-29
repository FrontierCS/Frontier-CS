import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    TARGET_SLACK_BUFFER_FACTOR = 0.5
    GUARANTEE_SLACK_FACTOR = 1.1

    def solve(self, spec_path: str) -> "Solution":
        self._cache_progress = 0.0
        self._cache_progress_time = -1.0

        initial_slack = self.deadline - self.task_duration
        if initial_slack > 0:
            self.target_finish_time = self.deadline - (initial_slack *
                                                       self.TARGET_SLACK_BUFFER_FACTOR)
        else:
            self.target_finish_time = self.deadline

        self.guarantee_threshold = self.restart_overhead * self.GUARANTEE_SLACK_FACTOR

        return self

    def _get_progress(self) -> float:
        if self._cache_progress_time == self.env.elapsed_seconds:
            return self._cache_progress

        progress = sum(end - start for start, end in self.task_done_time)

        self._cache_progress_time = self.env.elapsed_seconds
        self._cache_progress = progress
        return progress

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        progress = self._get_progress()
        work_remaining = self.task_duration - progress

        if work_remaining <= 1e-9:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_to_deadline = self.deadline - current_time
        current_slack = time_to_deadline - work_remaining

        if current_slack <= self.guarantee_threshold:
            return ClusterType.ON_DEMAND

        if self.target_finish_time > 0:
            target_progress = (current_time / self.target_finish_time) * self.task_duration
        else:
            target_progress = self.task_duration

        is_behind_schedule = progress < target_progress

        if has_spot:
            return ClusterType.SPOT

        if is_behind_schedule:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        args, _ = parser.parse_known_args()
        return cls(args)