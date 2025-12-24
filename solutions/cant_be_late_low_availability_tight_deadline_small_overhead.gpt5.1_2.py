import math

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except ImportError:  # Fallback definitions for local testing
    from enum import Enum

    class ClusterType(Enum):
        SPOT = "spot"
        ON_DEMAND = "on_demand"
        NONE = "none"

    class DummyEnv:
        def __init__(self):
            self.elapsed_seconds = 0.0
            self.gap_seconds = 60.0
            self.cluster_type = ClusterType.NONE

    class Strategy:
        def __init__(self, args=None):
            self.args = args
            self.env = DummyEnv()
            self.task_duration = 0.0
            self.task_done_time = []
            self.deadline = 0.0
            self.restart_overhead = 0.0


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__(args)
        self.args = args

        # Lazy-initialized scheduling parameters
        self._init_done = False
        self._slack_total = 0.0
        self._commit_slack_threshold = 0.0
        self._committed_to_od = False

        # Cached sum of task_done_time for efficiency
        self._cached_task_done_sum = 0.0
        self._cached_task_done_len = 0

    def solve(self, spec_path: str) -> "Solution":
        # Optional: could read spec_path here if needed
        return self

    def _lazy_init(self):
        if self._init_done:
            return

        # Total slack available if running with no further waste
        self._slack_total = float(self.deadline - self.task_duration)
        if self._slack_total < 0.0:
            # Negative slack: impossible deadline; treat as zero for robustness
            self._slack_total = 0.0

        # Commit to on-demand when remaining slack becomes small.
        # Use a fraction of total slack, but at least a multiple of restart_overhead.
        base_threshold = 0.25 * self._slack_total  # e.g., 1 hour when total slack is 4 hours
        min_threshold = 2.0 * float(self.restart_overhead)  # at least cover a couple of restarts
        self._commit_slack_threshold = max(min_threshold, base_threshold)

        # Threshold cannot exceed total slack
        if self._commit_slack_threshold > self._slack_total:
            self._commit_slack_threshold = self._slack_total

        self._init_done = True

    def _update_progress_cache(self):
        # Incrementally update cached sum of task_done_time
        lst = self.task_done_time
        n = len(lst)
        if n > self._cached_task_done_len:
            for i in range(self._cached_task_done_len, n):
                self._cached_task_done_sum += float(lst[i])
            self._cached_task_done_len = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._update_progress_cache()

        progress = self._cached_task_done_sum
        remaining_work = float(self.task_duration) - progress

        # If job already completed, do nothing to avoid extra cost
        if remaining_work <= 0.0:
            self._committed_to_od = True
            return ClusterType.NONE

        time_remaining = float(self.deadline) - float(self.env.elapsed_seconds)
        slack_remaining = time_remaining - remaining_work

        # Decide whether to permanently switch to on-demand
        if not self._committed_to_od:
            if slack_remaining <= self._commit_slack_threshold:
                self._committed_to_od = True

        # Once committed, always use on-demand while work remains
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Before commitment: use spot when available, otherwise on-demand
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
