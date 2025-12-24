import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cbl_adaptive_v2"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._initialized = False

        self._ema_p = 0.20
        self._p_tau_seconds = 2.0 * 3600.0  # time constant for availability EMA
        self._p_alpha = 0.03  # fallback if gap_seconds unknown

        self._last_has_spot: Optional[bool] = None
        self._up_run = 0.0
        self._down_run = 0.0
        self._mean_up = 1800.0   # 0.5h
        self._mean_down = 7200.0  # 2h
        self._run_beta = 0.20

        self._od_lock = False
        self._od_run_seconds = 0.0
        self._min_od_run_seconds = 1800.0  # 30 minutes

        self._gap_seconds_cache: Optional[float] = None

    def solve(self, spec_path: str) -> "Solution":
        self._initialized = True
        return self

    @staticmethod
    def _clamp(x: float, lo: float, hi: float) -> float:
        if x < lo:
            return lo
        if x > hi:
            return hi
        return x

    def _calc_work_done(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return 0.0
        if isinstance(tdt, (int, float)):
            return float(tdt)
        if not isinstance(tdt, (list, tuple)):
            return 0.0

        vals = []
        for v in tdt:
            if isinstance(v, (int, float)):
                vals.append(float(v))
        if not vals:
            return 0.0

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        s = sum(vals)
        last = vals[-1]
        mx = max(vals)

        # Heuristic: if list looks cumulative, use last; otherwise sum segments.
        if task_duration > 0:
            if s > 2.0 * task_duration and last <= 1.2 * task_duration and abs(last - mx) < 1e-9:
                nondecreasing = True
                prev = vals[0]
                for x in vals[1:]:
                    if x + 1e-9 < prev:
                        nondecreasing = False
                        break
                    prev = x
                if nondecreasing:
                    return last

        return s

    def _update_stats(self, has_spot: bool, dt: float) -> None:
        if self._gap_seconds_cache is None:
            self._gap_seconds_cache = dt
            if dt > 0 and self._p_tau_seconds > 0:
                self._p_alpha = 1.0 - math.exp(-dt / self._p_tau_seconds)
                self._p_alpha = self._clamp(self._p_alpha, 0.005, 0.20)

        a = self._p_alpha
        self._ema_p = (1.0 - a) * self._ema_p + a * (1.0 if has_spot else 0.0)

        if self._last_has_spot is None:
            self._last_has_spot = has_spot
            if has_spot:
                self._up_run += dt
            else:
                self._down_run += dt
            return

        if has_spot:
            self._up_run += dt
            if self._last_has_spot is False:
                # Down run ended
                dr = max(0.0, self._down_run)
                b = self._run_beta
                self._mean_down = (1.0 - b) * self._mean_down + b * dr
                self._mean_down = self._clamp(self._mean_down, 10.0 * dt, 8.0 * 3600.0)
                self._down_run = 0.0
        else:
            self._down_run += dt
            if self._last_has_spot is True:
                # Up run ended
                ur = max(0.0, self._up_run)
                b = self._run_beta
                self._mean_up = (1.0 - b) * self._mean_up + b * ur
                self._mean_up = self._clamp(self._mean_up, 10.0 * dt, 8.0 * 3600.0)
                self._up_run = 0.0

        self._last_has_spot = has_spot

    def _expected_remaining_down(self, dt: float) -> float:
        md = self._clamp(self._mean_down, 10.0 * dt, 8.0 * 3600.0)
        if self._last_has_spot is False:
            # If we've already been down longer than mean, assume "could end soon"
            if self._down_run >= md:
                return 2.0 * dt
            return max(2.0 * dt, md - self._down_run)
        return md

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = getattr(self, "env", None)
        dt = float(getattr(env, "gap_seconds", 300.0) or 300.0)
        if dt <= 0:
            dt = 300.0

        self._update_stats(has_spot, dt)

        if last_cluster_type == ClusterType.ON_DEMAND:
            self._od_run_seconds += dt
        else:
            self._od_run_seconds = 0.0

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        elapsed = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        work_done = self._calc_work_done()
        remaining_work = task_duration - work_done
        if remaining_work <= 1e-6:
            self._od_lock = False
            return ClusterType.NONE

        remaining_time = deadline - elapsed
        if remaining_time <= 1e-6:
            return ClusterType.NONE

        slack = remaining_time - remaining_work

        # Hard emergency: if we don't compute almost continuously, we risk missing deadline.
        emergency = (remaining_work + restart_overhead) >= (remaining_time - 0.25 * dt)

        p = self._clamp(self._ema_p, 0.01, 0.99)

        # How much OD compute we likely need, even if we take all expected spot uptime.
        needed_od = remaining_work - p * remaining_time
        if needed_od < 0.0:
            needed_od = 0.0
        needed_od_ratio = needed_od / max(remaining_work, 1.0)

        mean_down = self._clamp(self._mean_down, 10.0 * dt, 8.0 * 3600.0)

        # Engage OD lock if we're close enough that a typical spot outage would kill feasibility.
        if not self._od_lock:
            risk_reserve = restart_overhead + 0.80 * mean_down
            if emergency or slack <= risk_reserve or needed_od_ratio >= 0.95:
                self._od_lock = True

        # Once locked, stay on OD to guarantee completion.
        if self._od_lock:
            return ClusterType.ON_DEMAND

        # Not locked: exploit spot when available.
        if has_spot:
            # If we just started OD, keep it for a while (avoid thrashing overhead),
            # except when there's ample slack.
            if last_cluster_type == ClusterType.ON_DEMAND and self._od_run_seconds < self._min_od_run_seconds:
                if slack < 6.0 * 3600.0:
                    return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # Spot unavailable: decide between waiting (NONE) or using OD.
        exp_rem_down = self._expected_remaining_down(dt)

        # Preserve some slack for potential future outage + restart.
        # More aggressive OD when we believe we need significant OD time overall.
        reserve_wait = restart_overhead + max(exp_rem_down, 0.50 * mean_down) + needed_od_ratio * 0.50 * mean_down

        # If we wait this step, ensure we still could finish with OD afterwards (worst case spot never returns).
        must_start_od_now = (remaining_work + restart_overhead) >= (remaining_time - dt - 0.25 * dt)

        if not emergency and not must_start_od_now and slack > reserve_wait:
            return ClusterType.NONE

        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
