import math
import json
import os
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

    class Strategy:  # minimal fallback
        def __init__(self, args=None):
            self.args = args
            self.env = None


class Solution(Strategy):
    NAME = "cant_be_late_adaptive_v3"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self._inited = False

        self._steps_total = 0
        self._steps_spot_avail = 0

        self._prev_has_spot = None  # type: Optional[bool]
        self._AA = 0
        self._AU = 0
        self._UA = 0
        self._UU = 0

        # 0: spot when available, wait (NONE) when unavailable
        # 1: spot when available, OD when unavailable (with lock to reduce toggling)
        # 2: OD only
        self._mode = 0
        self._od_lock_steps = 0

        self._buffer_min_seconds = 900.0

    def solve(self, spec_path: str) -> "Solution":
        # Optional: read config if present
        try:
            if spec_path and os.path.exists(spec_path):
                with open(spec_path, "r") as f:
                    spec = json.load(f)
                buf = spec.get("safety_buffer_seconds")
                if isinstance(buf, (int, float)) and buf > 0:
                    self._buffer_min_seconds = float(buf)
        except Exception:
            pass

        self._inited = True
        return self

    @staticmethod
    def _safe_sum_done(task_done_time, task_duration: float) -> float:
        if not task_done_time:
            return 0.0
        td = task_done_time
        try:
            first = td[0]
        except Exception:
            return 0.0

        # list of numbers
        if isinstance(first, (int, float)):
            vals = []
            for x in td:
                if isinstance(x, (int, float)):
                    vals.append(float(x))
            if not vals:
                return 0.0
            if len(vals) >= 2 and all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1)):
                if vals[-1] <= task_duration + 1e-6:
                    return float(vals[-1])
            s = float(sum(vals))
            if s <= task_duration + 1e-6:
                return s
            # If sum seems too large, fall back to last (likely cumulative)
            return float(vals[-1])

        # list of (start, end)
        if isinstance(first, (tuple, list)) and len(first) >= 2:
            total = 0.0
            for seg in td:
                if isinstance(seg, (tuple, list)) and len(seg) >= 2:
                    a = seg[0]
                    b = seg[1]
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        d = float(b) - float(a)
                        if d > 0:
                            total += d
            return max(0.0, min(total, task_duration))

        # list of dicts
        if isinstance(first, dict):
            total = 0.0
            for seg in td:
                if isinstance(seg, dict):
                    d = seg.get("duration")
                    if isinstance(d, (int, float)) and d > 0:
                        total += float(d)
                    else:
                        a = seg.get("start")
                        b = seg.get("end")
                        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b > a:
                            total += float(b - a)
            return max(0.0, min(total, task_duration))

        return 0.0

    def _update_spot_stats(self, has_spot: bool) -> None:
        self._steps_total += 1
        if has_spot:
            self._steps_spot_avail += 1

        if self._prev_has_spot is not None:
            if self._prev_has_spot:
                if has_spot:
                    self._AA += 1
                else:
                    self._AU += 1
            else:
                if has_spot:
                    self._UA += 1
                else:
                    self._UU += 1
        self._prev_has_spot = has_spot

    def _estimate_markov(self):
        # Laplace smoothing
        a_u = (self._AU + 1.0) / (self._AA + self._AU + 2.0)  # P(A->U)
        u_a = (self._UA + 1.0) / (self._UA + self._UU + 2.0)  # P(U->A)
        p_stationary = u_a / max(u_a + a_u, 1e-12)
        p_obs = (self._steps_spot_avail + 1.0) / (self._steps_total + 2.0)
        # Blend: early rely more on observed marginal
        w = min(0.7, max(0.0, (self._steps_total - 20) / 200.0))
        p_eff = (1.0 - w) * p_obs + w * p_stationary
        return p_eff, a_u, u_a

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._inited:
            self._inited = True

        self._update_spot_stats(has_spot)

        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", float("inf")) or float("inf"))
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        done = self._safe_sum_done(getattr(self, "task_done_time", None), task_duration)
        remaining = max(0.0, task_duration - done)
        if remaining <= 0.0:
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        p_eff, _, u_a = self._estimate_markov()
        p_eff = max(0.01, min(0.99, p_eff))
        u_a = max(1e-3, min(0.999, u_a))

        buffer_sec = max(self._buffer_min_seconds, 2.0 * gap, 2.0 * restart_overhead)

        # Conservative guaranteed feasibility on OD from now
        od_switch_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead
        od_time_needed = remaining + od_switch_overhead

        if od_time_needed + buffer_sec >= time_left:
            self._mode = 2

        # If spot-wait expected completion likely misses deadline, upgrade to OD when no spot
        if self._mode == 0:
            wall_time_compute = remaining / p_eff
            wall_steps = wall_time_compute / max(gap, 1e-9)
            restart_rate_per_step = (1.0 - p_eff) * u_a
            exp_restarts = wall_steps * restart_rate_per_step
            expected_total = wall_time_compute + exp_restarts * restart_overhead
            if expected_total + buffer_sec >= time_left:
                self._mode = 1

        # If already in mode 1 and still extremely tight, go OD-only
        if self._mode == 1 and od_time_needed + 0.5 * buffer_sec >= time_left:
            self._mode = 2

        if self._mode == 2:
            return ClusterType.ON_DEMAND

        if self._mode == 1:
            if self._od_lock_steps > 0 and last_cluster_type == ClusterType.ON_DEMAND:
                self._od_lock_steps -= 1
                return ClusterType.ON_DEMAND

            if has_spot:
                if last_cluster_type == ClusterType.ON_DEMAND:
                    slack = time_left - od_time_needed
                    if slack > 6.0 * gap and p_eff > 0.55 and remaining > 4.0 * gap:
                        return ClusterType.SPOT
                    return ClusterType.ON_DEMAND
                return ClusterType.SPOT

            # no spot => OD, set lock to avoid rapid toggling
            lock_steps = int(math.ceil((restart_overhead + 0.5 * gap) / max(gap, 1e-9)))
            self._od_lock_steps = max(self._od_lock_steps, max(1, lock_steps))
            return ClusterType.ON_DEMAND

        # mode == 0: spot if available, else wait unless slack too low for expected return
        if has_spot:
            return ClusterType.SPOT

        # Estimate expected time until spot returns
        exp_wait = gap / u_a
        # If waiting likely burns too much slack, upgrade and use OD
        slack_now = time_left - od_time_needed
        if slack_now < exp_wait + buffer_sec:
            self._mode = 1
            self._od_lock_steps = max(1, int(math.ceil((restart_overhead + 0.5 * gap) / max(gap, 1e-9))))
            return ClusterType.ON_DEMAND

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
