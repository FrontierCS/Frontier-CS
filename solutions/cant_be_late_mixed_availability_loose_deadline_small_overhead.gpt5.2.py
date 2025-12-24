import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self._configured = False
        self._mode = 0  # 0=wait_when_no_spot, 1=no_wait, 2=critical(OD only)

        self._critical_slack = 0.0
        self._no_wait_slack = 0.0
        self._switch_to_spot_min_slack = 0.0

        self._done_cache_id = None
        self._done_cache_len = 0
        self._done_cache_sum = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _seg_to_seconds(seg: Any) -> float:
        if seg is None:
            return 0.0
        if isinstance(seg, (int, float)):
            v = float(seg)
            return v if v > 0.0 else 0.0
        if isinstance(seg, (list, tuple)):
            if len(seg) == 0:
                return 0.0
            if len(seg) == 1:
                try:
                    v = float(seg[0])
                    return v if v > 0.0 else 0.0
                except Exception:
                    return 0.0
            try:
                a = float(seg[0])
                b = float(seg[1])
                v = b - a
                return v if v > 0.0 else 0.0
            except Exception:
                return 0.0
        return 0.0

    def _get_done_seconds(self) -> float:
        t = getattr(self, "task_done_time", None)
        if t is None:
            self._done_cache_id = None
            self._done_cache_len = 0
            self._done_cache_sum = 0.0
            return 0.0

        if isinstance(t, (int, float)):
            v = float(t)
            self._done_cache_id = None
            self._done_cache_len = 0
            self._done_cache_sum = v if v > 0.0 else 0.0
            return self._done_cache_sum

        if not isinstance(t, (list, tuple)):
            return self._done_cache_sum

        tid = id(t)
        n = len(t)

        if self._done_cache_id == tid and n >= self._done_cache_len:
            s = self._done_cache_sum
            for i in range(self._done_cache_len, n):
                s += self._seg_to_seconds(t[i])
            self._done_cache_len = n
            self._done_cache_sum = s
            return s

        s = 0.0
        for seg in t:
            s += self._seg_to_seconds(seg)
        self._done_cache_id = tid
        self._done_cache_len = n
        self._done_cache_sum = s
        return s

    def _configure(self) -> None:
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        o = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        td = float(getattr(self, "task_duration", 0.0) or 0.0)

        # Conservative thresholds, scaled by task size and also aware of overhead/step size.
        critical = max(6.0 * o + 2.0 * gap, 0.01 * td, 15.0 * 60.0)  # >= 15 minutes
        no_wait = max(24.0 * o + 6.0 * gap, 0.05 * td, 60.0 * 60.0)  # >= 1 hour

        # Avoid overly conservative behavior with huge step sizes.
        if td > 0.0:
            critical = min(critical, 0.05 * td)
            no_wait = min(no_wait, 0.25 * td)

        # Ensure ordering
        if no_wait < critical:
            no_wait = critical

        self._critical_slack = critical
        self._no_wait_slack = no_wait
        self._switch_to_spot_min_slack = critical + 2.0 * o + gap

        self._configured = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._configured:
            self._configure()

        done = self._get_done_seconds()
        td = float(getattr(self, "task_duration", 0.0) or 0.0)
        work_remaining = td - done
        if work_remaining <= 1e-9:
            return ClusterType.NONE

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        remaining_time = deadline - elapsed

        if remaining_time <= 0.0:
            return ClusterType.NONE

        slack = remaining_time - work_remaining

        # Monotonic mode tightening
        if slack <= 0.0:
            self._mode = 2
        elif slack <= self._critical_slack:
            self._mode = 2
        elif self._mode == 0 and slack <= self._no_wait_slack:
            self._mode = 1

        if self._mode == 2:
            return ClusterType.ON_DEMAND

        if self._mode == 1:
            if has_spot:
                if last_cluster_type == ClusterType.ON_DEMAND and slack <= self._switch_to_spot_min_slack:
                    return ClusterType.ON_DEMAND
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # mode == 0: wait when spot is down, otherwise use spot
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
