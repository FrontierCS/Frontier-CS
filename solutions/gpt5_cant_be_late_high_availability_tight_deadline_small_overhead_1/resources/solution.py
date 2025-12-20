from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_scheduler_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self.commit_to_od = False
        self._paused_steps = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _buffer_seconds(self):
        # Dynamic safety buffer to account for step granularity and restart overhead.
        gap = getattr(self.env, "gap_seconds", 60.0)
        ro = getattr(self, "restart_overhead", 0.0)
        # Ensure buffer covers at least one full step plus overhead, preferably two steps if small
        return max(2 * gap, ro + gap)

    def _total_done(self):
        try:
            return sum(self.task_done_time) if self.task_done_time else 0.0
        except Exception:
            return 0.0

    def _need_commit(self, t_left, remaining_work):
        # Time needed if switching to OD now: remaining work + one restart overhead (if not already on OD)
        overhead_if_switch = 0.0
        if self.env.cluster_type != ClusterType.ON_DEMAND:
            overhead_if_switch = self.restart_overhead
        needed_if_od = remaining_work + overhead_if_switch
        return t_left <= (needed_if_od + self._buffer_seconds())

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done = self._total_done()
        remaining_work = max(self.task_duration - done, 0.0)
        if remaining_work <= 0.0:
            self.commit_to_od = False
            return ClusterType.NONE

        t_left = max(self.deadline - self.env.elapsed_seconds, 0.0)
        gap = self.env.gap_seconds

        # Reevaluate commit decision each step
        if not self.commit_to_od and self._need_commit(t_left, remaining_work):
            self.commit_to_od = True

        if self.commit_to_od:
            self._paused_steps = 0
            return ClusterType.ON_DEMAND

        # Not committed: prefer Spot when available
        if has_spot:
            self._paused_steps = 0
            return ClusterType.SPOT

        # Spot unavailable: decide to wait or start OD early
        # If waiting one step would make us miss the deadline (considering overhead), commit now.
        overhead_if_switch = self.restart_overhead
        buffer_sec = self._buffer_seconds()
        if (t_left - gap) <= (remaining_work + overhead_if_switch + buffer_sec):
            self.commit_to_od = True
            self._paused_steps = 0
            return ClusterType.ON_DEMAND

        # Otherwise wait this step for Spot
        self._paused_steps += 1
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
