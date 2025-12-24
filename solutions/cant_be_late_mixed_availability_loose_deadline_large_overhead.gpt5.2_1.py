import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self._locked_od = False

        self._prev_has_spot: Optional[bool] = None
        self._consec_up = 0
        self._consec_down = 0

        # Transition statistics for spot "up streak" length estimation.
        # Use priors so we don't assume streak length=1 at the beginning.
        self._up_steps = 10.0
        self._up_to_down = 2.0

        self._last_elapsed: Optional[float] = None
        self._last_done_total: Optional[float] = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _safe_float(x: Any, default: float = 0.0) -> float:
        try:
            return float(x)
        except Exception:
            return default

    def _get_done_total(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0
        if isinstance(tdt, (int, float)):
            return float(tdt)
        if not isinstance(tdt, (list, tuple)):
            return 0.0

        total = 0.0
        for seg in tdt:
            if isinstance(seg, (int, float)):
                total += float(seg)
                continue
            if isinstance(seg, (list, tuple)) and len(seg) >= 2:
                a, b = seg[0], seg[1]
                if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    total += float(b) - float(a)
                    continue
        if total < 0:
            total = 0.0
        return total

    def _maybe_reset_episode(self, elapsed: float, done_total: float) -> None:
        if self._last_elapsed is None or self._last_done_total is None:
            self._locked_od = False
            self._prev_has_spot = None
            self._consec_up = 0
            self._consec_down = 0
            self._up_steps = 10.0
            self._up_to_down = 2.0
            self._last_elapsed = elapsed
            self._last_done_total = done_total
            return

        if elapsed + 1e-9 < self._last_elapsed or done_total + 1e-9 < self._last_done_total or elapsed <= 1e-9:
            self._locked_od = False
            self._prev_has_spot = None
            self._consec_up = 0
            self._consec_down = 0
            self._up_steps = 10.0
            self._up_to_down = 2.0

    def _update_spot_stats(self, has_spot: bool) -> None:
        if has_spot:
            self._consec_up += 1
            self._consec_down = 0
        else:
            self._consec_down += 1
            self._consec_up = 0

        if self._prev_has_spot is True:
            self._up_steps += 1.0
            if not has_spot:
                self._up_to_down += 1.0

        self._prev_has_spot = has_spot

    def _expected_up_streak_steps(self) -> float:
        # Average up-streak length in steps ~ up_steps / up_to_down
        denom = max(self._up_to_down, 1e-9)
        return max(self._up_steps / denom, 1.0)

    def _buffer_seconds(self) -> float:
        gap = self._safe_float(getattr(self.env, "gap_seconds", 0.0), 0.0)
        ro = self._safe_float(getattr(self, "restart_overhead", 0.0), 0.0)
        return max(2.0 * gap, min(0.5 * ro, 900.0), 60.0)

    def _should_start_spot_from_nonspot(self, slack_seconds: float) -> bool:
        gap = self._safe_float(getattr(self.env, "gap_seconds", 0.0), 0.0)
        if gap <= 0:
            return True
        ro = self._safe_float(getattr(self, "restart_overhead", 0.0), 0.0)
        if ro <= 0:
            return True

        exp_steps = self._expected_up_streak_steps()
        exp_up_seconds = exp_steps * gap

        overhead_steps = int(math.ceil(ro / gap))

        # If we are running low on slack, take the spot opportunity.
        if slack_seconds <= 2.0 * ro + self._buffer_seconds():
            return True

        # If expected run isn't long enough to amortize overhead, be cautious:
        # require that we already observed a stable "up" streak.
        if exp_up_seconds < 1.25 * ro:
            return self._consec_up >= overhead_steps + 1

        # Mildly unstable: short probe.
        if exp_up_seconds < 2.5 * ro:
            return self._consec_up >= min(2, overhead_steps)

        return True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self._safe_float(getattr(self.env, "elapsed_seconds", 0.0), 0.0)
        done_total = self._get_done_total()
        self._maybe_reset_episode(elapsed, done_total)

        self._update_spot_stats(has_spot)

        task_duration = self._safe_float(getattr(self, "task_duration", 0.0), 0.0)
        deadline = self._safe_float(getattr(self, "deadline", float("inf")), float("inf"))
        restart_overhead = self._safe_float(getattr(self, "restart_overhead", 0.0), 0.0)

        remaining = max(task_duration - done_total, 0.0)
        time_left = max(deadline - elapsed, 0.0)
        slack = time_left - remaining
        buffer = self._buffer_seconds()

        self._last_elapsed = elapsed
        self._last_done_total = done_total

        if remaining <= 0.0:
            return ClusterType.NONE

        if last_cluster_type == ClusterType.ON_DEMAND:
            self._locked_od = True

        if self._locked_od:
            return ClusterType.ON_DEMAND

        od_start_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead
        if time_left <= remaining + od_start_overhead + buffer:
            self._locked_od = True
            return ClusterType.ON_DEMAND

        if has_spot:
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            if self._should_start_spot_from_nonspot(slack_seconds=slack):
                return ClusterType.SPOT
            return ClusterType.NONE

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
