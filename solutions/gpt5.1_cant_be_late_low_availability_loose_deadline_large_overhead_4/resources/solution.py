from typing import Any

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self.committed_to_on_demand = False
        self._policy_initialized = False
        self._cached_done_work = 0.0
        self._last_task_done_len = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _initialize_policy(self):
        try:
            initial_slack = float(self.deadline) - float(self.task_duration)
        except Exception:
            initial_slack = 0.0
        if initial_slack < 0.0:
            initial_slack = 0.0
        self.initial_slack = initial_slack

        try:
            dt = float(self.env.gap_seconds)
        except Exception:
            dt = 0.0
        try:
            ro = float(self.restart_overhead)
        except Exception:
            ro = 0.0

        commit_fraction = 0.25  # Reserve 25% of slack for safety

        if self.initial_slack > 0.0:
            commit_threshold = self.initial_slack * commit_fraction
            min_threshold = dt + ro
            if commit_threshold < min_threshold:
                commit_threshold = min_threshold
            max_threshold = self.initial_slack * 0.9
            if commit_threshold > max_threshold:
                commit_threshold = max_threshold
        else:
            commit_threshold = 0.0

        self.commit_threshold = commit_threshold
        self._policy_initialized = True

    def _update_done_work_cache(self) -> float:
        try:
            history = self.task_done_time
        except Exception:
            return 0.0
        if history is None:
            return 0.0

        length = len(history)
        if length > self._last_task_done_len:
            try:
                new_sum = sum(float(x) for x in history[self._last_task_done_len:length])
                self._cached_done_work += new_sum
            except Exception:
                total = 0.0
                for x in history:
                    try:
                        total += float(x)
                    except Exception:
                        pass
                self._cached_done_work = total
            self._last_task_done_len = length
        return self._cached_done_work

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._policy_initialized:
            self._initialize_policy()

        done_work = self._update_done_work_cache()

        try:
            task_duration = float(self.task_duration)
        except Exception:
            task_duration = 0.0

        remaining_work = task_duration - done_work
        if remaining_work <= 0.0:
            return ClusterType.NONE

        try:
            current_time = float(self.env.elapsed_seconds)
            deadline = float(self.deadline)
            time_left = deadline - current_time
        except Exception:
            return ClusterType.ON_DEMAND

        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        try:
            restart_overhead = float(self.restart_overhead)
        except Exception:
            restart_overhead = 0.0

        try:
            gap = float(self.env.gap_seconds)
        except Exception:
            gap = 0.0

        slack = time_left - (remaining_work + restart_overhead)

        if not self.committed_to_on_demand:
            if slack <= self.commit_threshold or slack <= 0.0:
                self.committed_to_on_demand = True

        if self.committed_to_on_demand:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if slack - gap >= self.commit_threshold and time_left - gap > 0.0:
            return ClusterType.NONE

        self.committed_to_on_demand = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
