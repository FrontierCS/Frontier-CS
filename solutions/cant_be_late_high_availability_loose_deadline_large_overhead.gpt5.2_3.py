import math
from collections import deque

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
            except Exception:
                pass
        self._args = args

        self._initialized = False
        self._od_mode = False

        self._last_work_done = 0.0
        self._last_elapsed = 0.0

        self._spot_time = 0.0
        self._spot_progress = 0.0

        self._od_time = 0.0
        self._od_progress = 0.0

        self._avail_window = None
        self._avail_true = 0

        self._last_has_spot = None
        self._seg_len = 0.0
        self._up_ema = None
        self._down_ema = None

        self._min_observe_seconds = 2.0 * 3600.0  # don't proactively switch too early
        self._z_wilson = 1.0  # ~68% lower bound

    def solve(self, spec_path: str) -> "Solution":
        self._initialized = False
        return self

    @staticmethod
    def _wilson_lower_bound(k: float, n: float, z: float) -> float:
        if n <= 0:
            return 0.0
        phat = k / n
        z2 = z * z
        denom = 1.0 + z2 / n
        center = phat + z2 / (2.0 * n)
        rad = z * math.sqrt((phat * (1.0 - phat) + z2 / (4.0 * n)) / n)
        lb = (center - rad) / denom
        if lb < 0.0:
            return 0.0
        if lb > 1.0:
            return 1.0
        return lb

    def _compute_work_done(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0
        if isinstance(td, (int, float)):
            return float(td)
        if isinstance(td, (list, tuple)):
            if not td:
                return 0.0
            first = td[0]
            if isinstance(first, (list, tuple)) and len(first) == 2:
                total = 0.0
                for seg in td:
                    try:
                        a, b = seg
                        total += max(0.0, float(b) - float(a))
                    except Exception:
                        continue
                return total
            if all(isinstance(x, (int, float)) for x in td):
                # Heuristic: if values look like cumulative progress, use last.
                try:
                    inc = True
                    for i in range(len(td) - 1):
                        if td[i] > td[i + 1]:
                            inc = False
                            break
                    last = float(td[-1])
                    s = float(sum(td))
                    task_dur = float(getattr(self, "task_duration", float("inf")))
                    if inc and last <= task_dur + 1e-6 and s <= last * 1.05:
                        return last
                    return s
                except Exception:
                    return float(sum(float(x) for x in td if isinstance(x, (int, float))))
        return 0.0

    def _init_if_needed(self):
        if self._initialized:
            return
        gap = float(getattr(self.env, "gap_seconds", 300.0))
        window_hours = 12.0
        window_len = max(24, int((window_hours * 3600.0) / max(gap, 1e-9)))
        self._avail_window = deque(maxlen=window_len)
        self._avail_true = 0
        self._initialized = True

    def _update_stats(self, last_cluster_type: ClusterType, has_spot: bool):
        self._init_if_needed()

        gap = float(getattr(self.env, "gap_seconds", 300.0))
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))

        # Progress delta from previous step
        work_done = self._compute_work_done()
        delta_work = work_done - self._last_work_done
        if delta_work < -1e-6:
            delta_work = 0.0

        if last_cluster_type == ClusterType.SPOT:
            self._spot_time += gap
            self._spot_progress += max(0.0, delta_work)
        elif last_cluster_type == ClusterType.ON_DEMAND:
            self._od_time += gap
            self._od_progress += max(0.0, delta_work)

        self._last_work_done = work_done
        self._last_elapsed = elapsed

        # Availability window stats
        if self._avail_window is not None:
            if len(self._avail_window) == self._avail_window.maxlen:
                old = self._avail_window[0]
                if old:
                    self._avail_true -= 1
            self._avail_window.append(bool(has_spot))
            if has_spot:
                self._avail_true += 1

        # Segment EMA for has_spot
        if self._last_has_spot is None:
            self._last_has_spot = bool(has_spot)
            self._seg_len = gap
        else:
            if bool(has_spot) == self._last_has_spot:
                self._seg_len += gap
            else:
                alpha = 0.15
                if self._last_has_spot:
                    if self._up_ema is None:
                        self._up_ema = self._seg_len
                    else:
                        self._up_ema = (1.0 - alpha) * self._up_ema + alpha * self._seg_len
                else:
                    if self._down_ema is None:
                        self._down_ema = self._seg_len
                    else:
                        self._down_ema = (1.0 - alpha) * self._down_ema + alpha * self._seg_len
                self._last_has_spot = bool(has_spot)
                self._seg_len = gap

    def _spot_efficiency_lb(self) -> float:
        # Efficiency of SPOT time converting into useful work (captures restart overhead observed).
        if self._spot_time <= 0.0:
            return 0.80
        eff = self._spot_progress / max(self._spot_time, 1e-9)
        eff = max(0.0, min(1.0, eff))

        # Conservative margin; more conservative with low data.
        if self._spot_time < 2.0 * 3600.0:
            return max(0.60, eff - 0.12)
        if self._spot_time < 6.0 * 3600.0:
            return max(0.65, eff - 0.10)
        return max(0.70, eff - 0.08)

    def _availability_lb(self) -> float:
        if self._avail_window is None or len(self._avail_window) == 0:
            return 0.0

        n = float(len(self._avail_window))
        k = float(self._avail_true)

        # Light prior to avoid extremely pessimistic early estimates.
        # Prior roughly equivalent to ~1 hour of observations at 60% availability.
        gap = float(getattr(self.env, "gap_seconds", 300.0))
        prior_n = max(6.0, min(24.0, 3600.0 / max(gap, 1e-9)))
        prior_p = 0.60
        n2 = n + prior_n
        k2 = k + prior_p * prior_n

        return self._wilson_lower_bound(k2, n2, self._z_wilson)

    def _should_switch_to_od(self, last_cluster_type: ClusterType, has_spot: bool) -> bool:
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 300.0))
        deadline = float(getattr(self, "deadline", float("inf")))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))
        task_duration = float(getattr(self, "task_duration", 0.0))

        work_done = self._last_work_done
        w_rem = max(0.0, task_duration - work_done)
        t_rem = max(0.0, deadline - elapsed)

        if w_rem <= 0.0:
            return False

        switch_overhead = restart_overhead if last_cluster_type != ClusterType.ON_DEMAND else 0.0

        # Emergency: if slack is small, commit to OD to guarantee completion.
        emergency_slack = max(5400.0, 3.0 * restart_overhead + 2.0 * gap)  # >= 1.5h
        slack_after_switch = t_rem - (w_rem + switch_overhead)
        if slack_after_switch <= emergency_slack:
            return True

        # If we haven't observed much yet, avoid proactive switch unless clearly infeasible.
        if elapsed < self._min_observe_seconds:
            # But don't risk infeasibility.
            if w_rem + switch_overhead + 2.0 * gap >= t_rem:
                return True
            return False

        p_lb = self._availability_lb()
        eff_lb = self._spot_efficiency_lb()
        net_rate_lb = max(1e-6, p_lb * eff_lb)

        # Predict remaining time needed if we keep using SPOT when available and pause otherwise.
        # Apply a modest margin to account for nonstationarity.
        t_needed_spot = (w_rem / net_rate_lb) * 1.08

        # Add some switching/setup buffer.
        buffer = switch_overhead + restart_overhead * 0.5 + 2.0 * gap
        if t_needed_spot + buffer >= t_rem:
            return True

        # If spot is currently unavailable and forecast says we'd be close, switch now.
        if not has_spot:
            if (t_needed_spot + buffer + 2.0 * restart_overhead) >= t_rem:
                return True

        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_stats(last_cluster_type, has_spot)

        task_duration = float(getattr(self, "task_duration", 0.0))
        work_done = self._last_work_done
        if task_duration > 0.0 and work_done >= task_duration - 1e-9:
            return ClusterType.NONE

        if self._od_mode:
            return ClusterType.ON_DEMAND

        if self._should_switch_to_od(last_cluster_type, has_spot):
            self._od_mode = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
