from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_guard_plus"

    def __init__(self, args=None):
        super().__init__(args)
        self._commit_to_od = False
        self._work_done_sum = 0.0
        self._last_task_index = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _update_work_done(self):
        lst = self.task_done_time
        try:
            n = len(lst)
            if n > self._last_task_index:
                # Sum new segments only
                added = 0.0
                for v in lst[self._last_task_index:]:
                    added += float(v)
                self._work_done_sum += added
                self._last_task_index = n
        except TypeError:
            # Fallback if task_done_time is not a list
            try:
                self._work_done_sum = float(lst) if lst is not None else 0.0
                self._last_task_index = 1
            except Exception:
                pass

    def _remaining_work(self) -> float:
        self._update_work_done()
        remain = self.task_duration - self._work_done_sum
        if remain < 0.0:
            remain = 0.0
        return remain

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to on-demand, keep it to avoid extra overhead/risk
        if self._commit_to_od:
            remaining = self._remaining_work()
            if remaining <= 0.0:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        # Calculate remaining work and time left
        remaining = self._remaining_work()
        if remaining <= 0.0:
            return ClusterType.NONE

        now = self.env.elapsed_seconds
        time_left = self.deadline - now
        if time_left <= 0.0:
            # Out of time: best-effort is on-demand
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Overhead if we switch to on-demand from current state
        switch_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead

        # Buffer to account for step discretization (commit one step early)
        margin = float(getattr(self.env, 'gap_seconds', 0.0) or 0.0)

        # If we can no longer delay and still guarantee completion with OD, commit now
        if time_left <= remaining + switch_overhead + margin:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, prefer spot if available; else wait (NONE)
        if has_spot:
            return ClusterType.SPOT

        # If spot is unavailable, we can pause as long as we maintain the deadline guard above
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)