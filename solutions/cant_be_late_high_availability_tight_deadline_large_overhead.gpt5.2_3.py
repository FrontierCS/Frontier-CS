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

    class Strategy:  # minimal stub
        def __init__(self, *args, **kwargs):
            pass


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Optional[Any] = None):
        self.args = args
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._inited = False
        self._forced_od = False
        self._on_od = False
        self._od_hold_until = 0.0

        self._prev_has_spot = None
        self._spot_steps = 0
        self._total_steps = 0
        self._spot_transitions_down = 0
        self._ema_avail = 0.7
        self._ema_down_rate = 0.0

        self._unavail_steps = 0

        self._max_wait_seconds = 3600.0
        self._min_od_run_seconds = 20.0 * 60.0
        self._base_buffer_seconds = 0.0
        self._avail_tau_seconds = 3600.0

    def solve(self, spec_path: str) -> "Solution":
        self._inited = False
        self._forced_od = False
        self._on_od = False
        self._od_hold_until = 0.0

        self._prev_has_spot = None
        self._spot_steps = 0
        self._total_steps = 0
        self._spot_transitions_down = 0
        self._ema_avail = 0.7
        self._ema_down_rate = 0.0
        self._unavail_steps = 0

        self._max_wait_seconds = 3600.0
        self._min_od_run_seconds = 20.0 * 60.0
        self._base_buffer_seconds = 0.0
        self._avail_tau_seconds = 3600.0
        return self

    @staticmethod
    def _safe_float(x: Any, default: float = 0.0) -> float:
        try:
            return float(x)
        except Exception:
            return default

    def _get_done_work(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0
        if isinstance(td, (int, float)):
            return float(td)
        try:
            if len(td) == 0:
                return 0.0
            last = self._safe_float(td[-1], 0.0)
            s = self._safe_float(sum(td), 0.0)
            task_d = self._safe_float(getattr(self, "task_duration", 0.0), 0.0)

            # Heuristic: if sum is implausibly large compared to task_duration, treat list as cumulative.
            if task_d > 0.0 and s > task_d * 1.5 and last <= task_d * 1.05:
                return max(0.0, last)

            return max(0.0, s if s >= last else last)
        except Exception:
            try:
                return max(0.0, self._safe_float(td[-1], 0.0))
            except Exception:
                return 0.0

    def _init_once(self):
        if self._inited:
            return
        ro = self._safe_float(getattr(self, "restart_overhead", 0.0), 0.0)

        # Conservative buffer so we can absorb a few interruptions and some spot downtime.
        # Tuned for typical 4h slack, 0.2h overhead, but remains safe across step sizes.
        self._base_buffer_seconds = max(0.5 * 3600.0, 3.0 * ro) + 0.35 * 3600.0
        self._inited = True

    def _update_spot_stats(self, has_spot: bool, dt: float, elapsed: float):
        self._total_steps += 1
        if has_spot:
            self._spot_steps += 1

        if self._prev_has_spot is not None:
            if self._prev_has_spot and (not has_spot):
                self._spot_transitions_down += 1
        self._prev_has_spot = has_spot

        # EMA availability with a 1h time constant (scaled by dt).
        tau = max(60.0, self._avail_tau_seconds)
        alpha = dt / (tau + dt) if dt > 0 else 0.05
        x = 1.0 if has_spot else 0.0
        self._ema_avail = (1.0 - alpha) * self._ema_avail + alpha * x

        # EMA of "down transitions per second" (volatility proxy).
        # Transition sample: 1/dt when down transition occurs else 0
        if dt > 0 and self._prev_has_spot is not None:
            down_transition = 1.0 / dt if (self._prev_has_spot and (not has_spot)) else 0.0
            self._ema_down_rate = (1.0 - alpha) * self._ema_down_rate + alpha * down_transition

    def _critical_buffer(self, time_left: float) -> float:
        ro = self._safe_float(getattr(self, "restart_overhead", 0.0), 0.0)

        avail = min(0.99, max(0.01, self._ema_avail))
        # More conservative if availability is low.
        avail_buffer = (1.0 - avail) * (1.5 * 3600.0)  # up to 1.5h

        # Volatility buffer based on expected down transitions ahead.
        # Keep small to avoid forcing OD too early.
        expected_down = max(0.0, self._ema_down_rate) * max(0.0, time_left)
        vol_buffer = min(1.0 * 3600.0, expected_down * ro * 0.30)

        buf = self._base_buffer_seconds + avail_buffer + vol_buffer
        return min(buf, 6.0 * 3600.0)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_once()

        dt = self._safe_float(getattr(self.env, "gap_seconds", 0.0), 0.0)
        elapsed = self._safe_float(getattr(self.env, "elapsed_seconds", 0.0), 0.0)

        if dt <= 0.0:
            dt = 60.0

        self._update_spot_stats(has_spot, dt, elapsed)

        done = self._get_done_work()
        task_d = self._safe_float(getattr(self, "task_duration", 0.0), 0.0)
        remaining_work = max(0.0, task_d - done)

        if remaining_work <= 0.0:
            return ClusterType.NONE

        deadline = self._safe_float(getattr(self, "deadline", 0.0), 0.0)
        time_left = max(0.0, deadline - elapsed)
        slack = time_left - remaining_work

        crit = self._critical_buffer(time_left)

        if self._forced_od or slack <= crit or time_left <= 0.0:
            self._forced_od = True
            self._on_od = True
            self._od_hold_until = float("inf")
            return ClusterType.ON_DEMAND

        if has_spot:
            self._unavail_steps = 0
            if self._on_od and elapsed < self._od_hold_until:
                return ClusterType.ON_DEMAND
            self._on_od = False
            return ClusterType.SPOT

        # No spot available: decide NONE vs ON_DEMAND based on slack we can spend waiting.
        self._unavail_steps += 1
        waited = self._unavail_steps * dt

        # Budget for waiting: only the slack above critical buffer, capped by max_wait_seconds.
        max_wait = min(self._max_wait_seconds, max(0.0, slack - crit))

        if waited < max_wait:
            return ClusterType.NONE

        # Switch to on-demand, hold for a bit to avoid thrashing.
        self._on_od = True
        self._od_hold_until = elapsed + self._min_od_run_seconds
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
