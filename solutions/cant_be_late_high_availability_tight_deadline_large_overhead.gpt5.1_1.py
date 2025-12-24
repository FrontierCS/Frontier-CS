from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_slack_v1"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _compute_progress(self) -> float:
        td = getattr(self, "task_done_time", 0.0)
        try:
            if isinstance(td, (int, float)):
                progress = float(td)
            else:
                progress = float(sum(td))
        except TypeError:
            progress = 0.0

        task_duration = getattr(self, "task_duration", None)
        try:
            if task_duration is not None:
                max_dur = float(task_duration)
                if progress > max_dur:
                    progress = max_dur
        except (TypeError, ValueError):
            pass

        return max(progress, 0.0)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not hasattr(self, "_force_on_demand"):
            self._force_on_demand = False

        progress = self._compute_progress()
        task_duration = getattr(self, "task_duration", 0.0) or 0.0
        work_remaining = max(0.0, float(task_duration) - progress)

        if work_remaining <= 0.0:
            return ClusterType.NONE

        elapsed = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
        deadline = getattr(self, "deadline", 0.0) or 0.0
        time_remaining = deadline - elapsed

        if time_remaining <= 0.0:
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        restart_overhead = getattr(self, "restart_overhead", 0.0) or 0.0
        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0

        commit_buffer = float(restart_overhead) + 2.0 * float(gap)

        if time_remaining <= work_remaining + commit_buffer:
            self._force_on_demand = True

        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
