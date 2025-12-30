import math
from typing import Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except TypeError:
                pass
        self._spec_path: Optional[str] = None
        self._reset_episode_state()

    def _reset_episode_state(self):
        self._committed_od = False
        self._done_sum = 0.0
        self._done_len = 0
        self._last_elapsed = -1.0

    def solve(self, spec_path: str) -> "Solution":
        self._spec_path = spec_path
        return self

    def _update_done_work(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            self._done_sum = 0.0
            self._done_len = 0
            return 0.0
        n = len(tdt)
        if n < self._done_len:
            self._done_sum = float(sum(tdt))
            self._done_len = n
            return self._done_sum
        if n > self._done_len:
            self._done_sum += float(sum(tdt[self._done_len:]))
            self._done_len = n
        return self._done_sum

    def _safety_margin(self) -> float:
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        # Conservative buffer for step discretization + evaluator bookkeeping.
        return max(2.0 * gap, 60.0)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = getattr(self, "env", None)
        elapsed = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)

        if self._last_elapsed < 0:
            self._last_elapsed = elapsed
        elif elapsed + 1e-9 < self._last_elapsed:
            self._reset_episode_state()
            self._last_elapsed = elapsed
        else:
            self._last_elapsed = elapsed

        done_work = self._update_done_work()
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        remaining_work = task_duration - done_work
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        remaining_slack = time_left - remaining_work
        safety = self._safety_margin()

        if self._committed_od:
            return ClusterType.ON_DEMAND

        od_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead

        # Hard safety: ensure we can finish if we switch to on-demand immediately.
        if remaining_slack <= od_overhead + safety:
            self._committed_od = True
            return ClusterType.ON_DEMAND

        if has_spot:
            # If (re)starting spot (i.e., last step wasn't spot), require enough slack
            # to tolerate: spot restart overhead now + potential on-demand restart later.
            if last_cluster_type != ClusterType.SPOT:
                if remaining_slack <= (restart_overhead + od_overhead + safety):
                    self._committed_od = True
                    return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # No spot available: wait for spot until it's no longer safe, then on-demand.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)