import math
from typing import Any, Optional

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:  # pragma: no cover
    from enum import Enum

    class ClusterType(Enum):
        SPOT = 1
        ON_DEMAND = 2
        NONE = 3

    class Strategy:  # minimal stub for local execution
        def __init__(self, args: Any = None):
            self.args = args
            self.env = None


class Solution(Strategy):
    NAME = "lazy_spot_guard_v1"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self._no_switch_until: float = 0.0
        self._prefer_od_until: float = 0.0

        self._done_ref: Optional[list] = None
        self._done_len: int = 0
        self._done_sum: float = 0.0
        self._done_is_cumulative: Optional[bool] = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _completed_work_seconds(self) -> float:
        lst = getattr(self, "task_done_time", None)
        if not lst:
            self._done_ref = lst
            self._done_len = 0
            self._done_sum = 0.0
            self._done_is_cumulative = None
            return 0.0

        if not isinstance(lst, list):
            try:
                v = float(lst)
            except Exception:
                return 0.0
            return max(0.0, min(v, float(getattr(self, "task_duration", v))))

        if self._done_ref is not lst or self._done_len > len(lst):
            self._done_ref = lst
            self._done_len = 0
            self._done_sum = 0.0
            self._done_is_cumulative = None

        if self._done_is_cumulative is True:
            try:
                v = float(lst[-1])
            except Exception:
                v = 0.0
            td = float(getattr(self, "task_duration", v))
            return max(0.0, min(v, td))

        if self._done_len < len(lst):
            add = 0.0
            for x in lst[self._done_len :]:
                try:
                    add += float(x)
                except Exception:
                    pass
            self._done_sum += add
            self._done_len = len(lst)

        td = float(getattr(self, "task_duration", 0.0))
        if self._done_is_cumulative is None and len(lst) >= 5 and td > 0:
            s = self._done_sum
            try:
                last = float(lst[-1])
            except Exception:
                last = 0.0
            if last <= td * 1.05 and s > td * 1.2:
                nondecreasing = True
                try:
                    for i in range(len(lst) - 1):
                        if float(lst[i]) > float(lst[i + 1]) + 1e-9:
                            nondecreasing = False
                            break
                except Exception:
                    nondecreasing = False
                if nondecreasing:
                    self._done_is_cumulative = True
                    return max(0.0, min(last, td))
                self._done_is_cumulative = False
            elif s <= td * 1.05:
                self._done_is_cumulative = False

        return max(0.0, min(self._done_sum, td if td > 0 else self._done_sum))

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = self.env
        now = float(getattr(env, "elapsed_seconds", 0.0))
        gap = float(getattr(env, "gap_seconds", 0.0))
        ro = float(getattr(self, "restart_overhead", 0.0))
        deadline = float(getattr(self, "deadline", 0.0))
        task_duration = float(getattr(self, "task_duration", 0.0))

        completed = self._completed_work_seconds()
        remaining = task_duration - completed
        if remaining <= 1e-6:
            return ClusterType.NONE

        time_left = deadline - now
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        # Conservative "can still finish if OD from now" slack:
        # includes one restart overhead, regardless of current state.
        slack = time_left - (remaining + ro)

        # If we are extremely tight, never wait.
        if slack <= 0.0:
            if last_cluster_type != ClusterType.ON_DEMAND:
                self._no_switch_until = max(self._no_switch_until, now + ro)
                self._prefer_od_until = max(self._prefer_od_until, now + max(ro, 2.0 * gap))
            return ClusterType.ON_DEMAND

        # Avoid switching during (estimated) restart overhead window unless forced.
        if now < self._no_switch_until:
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            if last_cluster_type == ClusterType.SPOT and has_spot:
                return ClusterType.SPOT

        # Waiting threshold: only wait if we can safely waste at least one more step plus small buffer.
        buffer_seconds = max(60.0, 0.05 * gap)
        wait_threshold = gap + buffer_seconds

        if has_spot:
            # If we recently started OD, keep it briefly to avoid thrashing.
            if last_cluster_type == ClusterType.ON_DEMAND and now < self._prefer_od_until:
                return ClusterType.ON_DEMAND

            # If currently on-demand, only switch back to spot if we can afford two restarts (OD->SPOT and back).
            if last_cluster_type == ClusterType.ON_DEMAND:
                slack_two_restarts = time_left - (remaining + 2.0 * ro)
                if slack_two_restarts > wait_threshold:
                    self._no_switch_until = max(self._no_switch_until, now + ro)
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND

            if last_cluster_type != ClusterType.SPOT:
                self._no_switch_until = max(self._no_switch_until, now + ro)
            return ClusterType.SPOT

        # No spot available.
        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        if slack > wait_threshold:
            return ClusterType.NONE

        self._no_switch_until = max(self._no_switch_until, now + ro)
        self._prefer_od_until = max(self._prefer_od_until, now + max(ro, 2.0 * gap))
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)