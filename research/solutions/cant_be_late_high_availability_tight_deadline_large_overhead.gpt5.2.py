import math
from typing import Any, Optional

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:  # pragma: no cover
    from enum import Enum

    class ClusterType(Enum):
        SPOT = "spot"
        ON_DEMAND = "on_demand"
        NONE = "none"

    class Strategy:
        def __init__(self, args=None):
            self.args = args
            self.env = None
            self.task_duration = 0.0
            self.task_done_time = []
            self.deadline = 0.0
            self.restart_overhead = 0.0


class Solution(Strategy):
    NAME = "cant_be_late_jit_od_v1"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self._committed_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _done_seconds(self) -> float:
        t = getattr(self, "task_done_time", None)
        if t is None:
            return 0.0
        if isinstance(t, (int, float)):
            return float(t)
        if not isinstance(t, (list, tuple)) or len(t) == 0:
            return 0.0
        try:
            if all(isinstance(x, (int, float)) for x in t):
                nondec = True
                for i in range(len(t) - 1):
                    if float(t[i]) > float(t[i + 1]) + 1e-9:
                        nondec = False
                        break
                if nondec:
                    return float(t[-1])
                return float(sum(float(x) for x in t))
            if all(isinstance(x, (list, tuple)) and len(x) >= 2 for x in t):
                total = 0.0
                for seg in t:
                    a, b = seg[0], seg[1]
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        total += max(0.0, float(b) - float(a))
                return float(total)
        except Exception:
            return 0.0
        return 0.0

    def _od_needed(self, remaining: float, last_cluster_type: ClusterType) -> float:
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        if last_cluster_type == ClusterType.ON_DEMAND:
            return remaining
        return remaining + overhead

    def _safety_commit(self) -> float:
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        return 2.0 * gap + 0.05 * overhead

    def _safety_next(self) -> float:
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        return 1.0 * gap + 0.05 * overhead

    def _safe_to_delay_one_step(self, remaining: float, time_left: float, last_cluster_type: ClusterType, action: ClusterType) -> bool:
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        if gap <= 0.0:
            return time_left > self._od_needed(remaining, last_cluster_type) + self._safety_commit()

        progress_lb = 0.0
        if action == ClusterType.SPOT:
            if last_cluster_type == ClusterType.SPOT:
                progress_lb = gap
            else:
                progress_lb = max(0.0, gap - overhead)
        elif action == ClusterType.ON_DEMAND:
            progress_lb = max(0.0, gap - (0.0 if last_cluster_type == ClusterType.ON_DEMAND else overhead))
        else:
            progress_lb = 0.0

        remaining_after = max(0.0, remaining - progress_lb)
        time_left_after = time_left - gap

        if time_left_after <= 0.0:
            return remaining_after <= 1e-9

        # Next step: assume we might need to switch to on-demand (worst-case no spot).
        od_needed_next = remaining_after + (0.0 if action == ClusterType.ON_DEMAND else overhead)
        return time_left_after >= od_needed_next + self._safety_next()

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        time_left = deadline - elapsed

        done = self._done_seconds()
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        remaining = max(0.0, task_duration - done)

        if remaining <= 1e-9:
            return ClusterType.NONE

        if time_left <= 0.0:
            self._committed_od = True
            return ClusterType.ON_DEMAND

        if self._committed_od:
            return ClusterType.ON_DEMAND

        # Commit to on-demand if required to guarantee deadline.
        od_needed_now = self._od_needed(remaining, last_cluster_type)
        if time_left <= od_needed_now + self._safety_commit():
            self._committed_od = True
            return ClusterType.ON_DEMAND

        if has_spot:
            # Use spot if we can still guarantee finishing by switching to OD next step (worst-case).
            if self._safe_to_delay_one_step(remaining, time_left, last_cluster_type, ClusterType.SPOT):
                return ClusterType.SPOT
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # No spot: wait if safe, else use OD.
        if self._safe_to_delay_one_step(remaining, time_left, last_cluster_type, ClusterType.NONE):
            return ClusterType.NONE

        self._committed_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)