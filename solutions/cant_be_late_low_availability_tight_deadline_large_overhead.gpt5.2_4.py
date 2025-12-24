import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_slack_hysteresis_v1"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self._reset_internal()

    def _reset_internal(self) -> None:
        self._last_has_spot: Optional[bool] = None
        self._uu = 1
        self._ud = 1
        self._du = 1
        self._dd = 1
        self._n_steps = 0
        self._n_up = 0

        self._commit_od = False
        self._od_lock_remaining = 0
        self._cached_gap: Optional[float] = None
        self._cached_over: Optional[float] = None
        self._wait_buffer_seconds: Optional[float] = None
        self._commit_margin_seconds: Optional[float] = None
        self._min_up_to_switch_seconds: Optional[float] = None
        self._min_od_lock_steps: Optional[int] = None

    def solve(self, spec_path: str) -> "Solution":
        self._reset_internal()
        return self

    @staticmethod
    def _is_number(x: Any) -> bool:
        return isinstance(x, (int, float)) and not isinstance(x, bool)

    def _compute_done_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return 0.0

        try:
            first = tdt[0]
        except Exception:
            return 0.0

        if self._is_number(first):
            vals = []
            try:
                for v in tdt:
                    if self._is_number(v):
                        vals.append(float(v))
            except Exception:
                return 0.0

            if not vals:
                return 0.0

            is_non_decreasing = True
            for i in range(len(vals) - 1):
                if vals[i] > vals[i + 1] + 1e-9:
                    is_non_decreasing = False
                    break

            if is_non_decreasing and vals[-1] <= float(getattr(self, "task_duration", 0.0)) + 1e-6:
                s = sum(vals)
                if s > vals[-1] * 1.2:
                    return s
                return vals[-1]

            return sum(vals)

        if isinstance(first, (tuple, list)) and len(first) >= 2:
            total = 0.0
            for seg in tdt:
                if isinstance(seg, (tuple, list)) and len(seg) >= 2 and self._is_number(seg[0]) and self._is_number(seg[1]):
                    total += max(0.0, float(seg[1]) - float(seg[0]))
            return total

        return 0.0

    def _update_markov(self, has_spot: bool) -> None:
        self._n_steps += 1
        if has_spot:
            self._n_up += 1

        if self._last_has_spot is None:
            self._last_has_spot = has_spot
            return

        prev = self._last_has_spot
        cur = has_spot
        if prev and cur:
            self._uu += 1
        elif prev and (not cur):
            self._ud += 1
        elif (not prev) and cur:
            self._du += 1
        else:
            self._dd += 1
        self._last_has_spot = has_spot

    def _expected_up_run_seconds(self, gap: float) -> float:
        denom = self._uu + self._ud
        p_stay = self._uu / denom if denom > 0 else 0.5
        p_stay = min(0.999999, max(0.0, p_stay))
        e_steps = 1.0 / max(1e-6, 1.0 - p_stay)
        return e_steps * gap

    def _ensure_params(self, gap: float, over: float) -> None:
        if self._cached_gap == gap and self._cached_over == over and self._wait_buffer_seconds is not None:
            return
        self._cached_gap = gap
        self._cached_over = over

        self._min_od_lock_steps = max(1, int(math.ceil(over / max(1.0, gap))))
        self._min_up_to_switch_seconds = max(over * 1.5, over + gap)

        # Slack usage policy:
        # - wait_buffer_seconds: keep at least this much slack in reserve (do not spend it on NONE)
        # - commit_margin_seconds: when slack is below this, commit to on-demand to avoid deadline risk
        self._wait_buffer_seconds = max(2.5 * over + 6.0 * gap, 0.75 * 3600.0)
        self._commit_margin_seconds = max(1.5 * over + 4.0 * gap, 0.35 * 3600.0)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        over = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        self._ensure_params(gap, over)

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        time_left = deadline - elapsed
        if time_left <= 0:
            return ClusterType.NONE

        done = self._compute_done_seconds()
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        remaining = task_duration - done
        if remaining <= 0:
            return ClusterType.NONE

        self._update_markov(has_spot)

        slack = time_left - remaining

        # Hard safety: if slack too low, commit to on-demand to reduce restart churn and deadline risk.
        if slack <= (self._commit_margin_seconds or 0.0):
            self._commit_od = True

        # Decrement lock if it is active (lock means: keep using on-demand for a few steps after switching).
        if self._od_lock_remaining > 0:
            self._od_lock_remaining -= 1
            if self._commit_od:
                return ClusterType.ON_DEMAND
            # If slack becomes large again (rare), allow breaking lock only if spot is available and likely stable.
            # Otherwise, keep ON_DEMAND during the lock.
            if has_spot:
                e_up = self._expected_up_run_seconds(gap)
                if slack > (self._wait_buffer_seconds or 0.0) * 1.25 and e_up >= (self._min_up_to_switch_seconds or 0.0) * 1.25:
                    return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        if self._commit_od:
            return ClusterType.ON_DEMAND

        if has_spot:
            # If we are currently on-demand, only switch to spot if the spot up-run is expected to last long enough.
            if last_cluster_type == ClusterType.ON_DEMAND:
                e_up = self._expected_up_run_seconds(gap)
                if slack > (self._wait_buffer_seconds or 0.0) and e_up >= (self._min_up_to_switch_seconds or 0.0):
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # No spot available this step.
        # Use slack to wait (NONE) during down periods, but keep a buffer.
        if slack > (self._wait_buffer_seconds or 0.0):
            return ClusterType.NONE

        # Need to make progress: use on-demand and lock for a few steps to avoid thrashing.
        if last_cluster_type != ClusterType.ON_DEMAND:
            self._od_lock_remaining = int(self._min_od_lock_steps or 1)
            if self._od_lock_remaining > 0:
                self._od_lock_remaining -= 1
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
