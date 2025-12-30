from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None, *extra_args, **kwargs):
        # Be robust to different Strategy.__init__ signatures.
        try:
            super().__init__(args, *extra_args, **kwargs)
        except TypeError:
            try:
                super().__init__()
            except TypeError:
                pass
        self.args = args
        self.od_only = False
        self._work_done_cache = 0.0
        self._last_done_len = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _update_work_done_cache(self):
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            self._work_done_cache = 0.0
            self._last_done_len = 0
            return
        try:
            length = len(tdt)
        except TypeError:
            self._work_done_cache = 0.0
            self._last_done_len = 0
            return
        if length != self._last_done_len:
            try:
                self._work_done_cache = float(sum(tdt))
            except TypeError:
                self._work_done_cache = 0.0
            self._last_done_len = length

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update cached completed work
        self._update_work_done_cache()

        env = self.env
        gap = float(getattr(env, "gap_seconds", 0.0))
        elapsed = float(getattr(env, "elapsed_seconds", 0.0))

        deadline = float(self.deadline)
        task_duration = float(self.task_duration)
        restart_overhead = float(self.restart_overhead)

        work_done = self._work_done_cache
        remaining_work = max(task_duration - work_done, 0.0)
        time_left = deadline - elapsed

        # If no work remaining or no time left, do nothing
        if remaining_work <= 0.0 or time_left <= 0.0:
            return ClusterType.NONE

        # Slack = extra time beyond required compute if we ran at full speed
        slack = time_left - remaining_work
        total_slack = max(deadline - task_duration, 0.0)

        # Buffer to account for discrete step size
        buffer = gap

        # Threshold for switching permanently to on-demand
        commit_slack = restart_overhead + buffer

        # Enter on-demand-only mode once slack is small
        if (not self.od_only) and slack <= commit_slack:
            self.od_only = True

        # Once committed, always use on-demand while work remains
        if self.od_only:
            return ClusterType.ON_DEMAND

        # Pre-commit phase
        # Allow idling (NONE) when slack is high and spot is unavailable
        idle_slack_threshold = max(commit_slack + 2.0 * gap, 0.5 * total_slack)

        # Use spot whenever available in pre-commit phase
        if has_spot:
            return ClusterType.SPOT

        # Spot not available
        if slack > idle_slack_threshold:
            # Plenty of slack: wait for spot
            return ClusterType.NONE

        # Moderate slack: fall back to on-demand when spot is unavailable
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)