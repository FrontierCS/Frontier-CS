from typing import Any, Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_guard_threshold_v3"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args
        self._reset_internal_state()

    def _reset_internal_state(self):
        self.lock_on_od: bool = False
        self._done_sum: float = 0.0
        self._last_done_len: int = 0
        self._prev_elapsed: float = -1.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _progress_sum(self) -> float:
        try:
            lst = self.task_done_time
        except Exception:
            return 0.0
        if not isinstance(lst, list):
            try:
                return float(lst)
            except Exception:
                return 0.0
        n = len(lst)
        if n == self._last_done_len:
            return self._done_sum
        # Incremental update
        if n > self._last_done_len:
            add = 0.0
            for i in range(self._last_done_len, n):
                try:
                    add += float(lst[i])
                except Exception:
                    continue
            self._done_sum += add
            self._last_done_len = n
            return self._done_sum
        # If list shrank (new episode), recompute
        total = 0.0
        for v in lst:
            try:
                total += float(v)
            except Exception:
                continue
        self._done_sum = total
        self._last_done_len = n
        return self._done_sum

    def _maybe_reset_for_new_episode(self):
        # Detect new episode by elapsed time reset or negative time
        t = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
        if self._prev_elapsed < 0 or t < self._prev_elapsed or t == 0.0 and self._prev_elapsed != 0.0:
            self._reset_internal_state()
        self._prev_elapsed = t

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._maybe_reset_for_new_episode()

        # If we already decided to lock on OD, stick to it
        if self.lock_on_od:
            return ClusterType.ON_DEMAND

        # Gather environment parameters with safe fallbacks
        dt = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        t = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        # Remaining work
        done = self._progress_sum()
        remaining = max(0.0, task_duration - done)

        # If already done, no need to spend more
        if remaining <= 1e-9:
            return ClusterType.NONE

        slack = deadline - t

        # Safety overhead cushion to guarantee we can switch to OD later and still finish
        safety_overhead = restart_overhead

        # If we cannot even afford the overhead to switch at all later, start OD now
        if slack <= remaining + safety_overhead + 1e-9:
            self.lock_on_od = True
            return ClusterType.ON_DEMAND

        # Can we afford to wait exactly one step (dt) before switching to OD and still finish?
        can_wait_one_step = slack >= remaining + dt + safety_overhead - 1e-9

        if has_spot:
            if can_wait_one_step:
                return ClusterType.SPOT
            else:
                self.lock_on_od = True
                return ClusterType.ON_DEMAND
        else:
            if can_wait_one_step:
                return ClusterType.NONE
            else:
                self.lock_on_od = True
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
