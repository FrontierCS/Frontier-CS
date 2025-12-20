from typing import Any, List, Tuple, Optional
import math

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_waiter_v2"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self._lock_on_demand = False
        self._last_decision: Optional[ClusterType] = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _sum_done_seconds(self) -> float:
        total = 0.0
        segs = getattr(self, "task_done_time", None)
        if not segs:
            return 0.0
        # Handle both plain durations and (start, end) tuples
        for seg in segs:
            if isinstance(seg, (int, float)):
                total += float(seg)
            elif isinstance(seg, (list, tuple)) and len(seg) >= 2:
                a, b = seg[0], seg[1]
                try:
                    total += float(b) - float(a)
                except Exception:
                    continue
            else:
                # Unknown format; ignore
                continue
        if not math.isfinite(total) or total < 0:
            return 0.0
        return total

    def _remaining_work(self) -> float:
        done = self._sum_done_seconds()
        remain = float(self.task_duration) - done
        if remain < 0:
            remain = 0.0
        return remain

    def _time_left(self) -> float:
        return max(0.0, float(self.deadline) - float(self.env.elapsed_seconds))

    def _safe_margin(self) -> float:
        # Safety margin to account for step discretization and restart uncertainty
        gap = float(self.env.gap_seconds)
        ro = float(self.restart_overhead)
        # Use a moderate margin: at least one gap + small constant, and at least half restart overhead
        return max(gap + 60.0, 0.5 * ro)

    def _must_lock_to_od(self, remain: float, t_left: float) -> bool:
        if remain <= 0:
            return False
        # If we must start OD now to guarantee finish, lock
        margin = self._safe_margin()
        threshold = remain + float(self.restart_overhead) + margin
        return t_left <= threshold

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already locked on OD, keep it until completion
        remain = self._remaining_work()
        if remain <= 0:
            self._lock_on_demand = False
            self._last_decision = ClusterType.NONE
            return ClusterType.NONE

        t_left = self._time_left()

        # If time already insufficient, must use OD (environment will penalize late finish, but try best)
        if t_left <= 0:
            self._lock_on_demand = True
            self._last_decision = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND

        if self._lock_on_demand:
            self._last_decision = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND

        # Determine if we must lock into OD now to finish on time
        if self._must_lock_to_od(remain, t_left):
            self._lock_on_demand = True
            self._last_decision = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND

        # Otherwise, prefer spot if available
        if has_spot:
            self._last_decision = ClusterType.SPOT
            return ClusterType.SPOT

        # Spot not available: Decide to wait (NONE) or switch to OD.
        # If after waiting one more step we still won't need to lock, wait; else switch to OD.
        gap = float(self.env.gap_seconds)
        margin = self._safe_margin()
        if (t_left - gap) > (remain + float(self.restart_overhead) + margin):
            decision = ClusterType.NONE
        else:
            self._lock_on_demand = True
            decision = ClusterType.ON_DEMAND

        self._last_decision = decision
        return decision

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
