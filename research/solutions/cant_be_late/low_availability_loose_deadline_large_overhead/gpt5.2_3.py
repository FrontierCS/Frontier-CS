import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "adaptive_deadline_spot_v3"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self._initialized = False

        self._last_elapsed: Optional[float] = None
        self._last_done: Optional[float] = None
        self._last_action: Optional[ClusterType] = None
        self._last_has_spot: Optional[bool] = None

        self._steps_obs = 0
        self._spot_obs = 0

        self._spot_streak = 0
        self._prev_spot_streak = 0
        self._avg_on_steps = 12.0
        self._avg_on_alpha = 0.15

        self._od_hold_steps = 0
        self._min_spot_confirm = 1
        self._min_od_hold = 1

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        self._min_spot_confirm = max(1, int(math.ceil(ro / max(1.0, gap))) + 1)
        self._min_od_hold = max(1, int(math.ceil(ro / max(1.0, gap))) + 1)
        self._initialized = True

    def _sum_done_time(self) -> float:
        # Try best-effort ways to infer completed work seconds.
        for obj in (self, getattr(self, "env", None)):
            if obj is None:
                continue
            val = getattr(obj, "task_done_seconds", None)
            if isinstance(val, (int, float)):
                return float(val)
            val = getattr(obj, "done_seconds", None)
            if isinstance(val, (int, float)):
                return float(val)
            val = getattr(obj, "progress_seconds", None)
            if isinstance(val, (int, float)):
                return float(val)

        tdt = getattr(self, "task_done_time", None)
        if isinstance(tdt, (int, float)):
            return float(tdt)

        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)

        if isinstance(tdt, list) and tdt:
            first = tdt[0]
            if isinstance(first, (int, float)):
                vals = [float(x) for x in tdt if isinstance(x, (int, float))]
                if not vals:
                    return 0.0
                nondecreasing = True
                for i in range(len(vals) - 1):
                    if vals[i] > vals[i + 1]:
                        nondecreasing = False
                        break
                if nondecreasing and vals[-1] > 4.0 * gap and vals[-1] <= 1.2 * max(task_duration, 1.0):
                    return float(vals[-1])
                return float(sum(vals))
            if isinstance(first, (tuple, list)) and len(first) >= 2:
                total = 0.0
                for seg in tdt:
                    if isinstance(seg, (tuple, list)) and len(seg) >= 2:
                        a, b = seg[0], seg[1]
                        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                            total += max(0.0, float(b) - float(a))
                return total
            if isinstance(first, dict):
                total = 0.0
                for item in tdt:
                    if not isinstance(item, dict):
                        continue
                    if "duration" in item and isinstance(item["duration"], (int, float)):
                        total += max(0.0, float(item["duration"]))
                    elif "start" in item and "end" in item:
                        a, b = item["start"], item["end"]
                        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                            total += max(0.0, float(b) - float(a))
                return total

        return 0.0

    def _estimate_p_spot_low(self) -> float:
        # Conservative estimate of future spot availability using a beta prior + 1-sigma lower bound.
        n = self._steps_obs
        s = self._spot_obs
        a = 2.0
        b = 10.0
        neff = n + a + b
        p = (s + a) / max(1.0, neff)
        var = p * (1.0 - p) / max(1.0, neff + 1.0)
        p_low = p - 1.0 * math.sqrt(max(0.0, var))
        return max(0.02, min(0.98, p_low))

    def _spot_efficiency(self) -> float:
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        avg_on_sec = max(gap, self._avg_on_steps * gap)
        if ro <= 0.0:
            return 1.0
        eff = avg_on_sec / (avg_on_sec + ro)
        return max(0.35, min(1.0, eff))

    def _time_tight(self, remaining_time: float, remaining_work: float) -> bool:
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        safety = 2.5 * ro + 2.0 * gap
        return remaining_time <= remaining_work + safety

    def _should_switch_od_to_spot(self, remaining_time: float, remaining_work: float) -> bool:
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        if remaining_work <= 0.0:
            return False

        # Avoid switching when close to deadline.
        if remaining_time <= remaining_work + 6.0 * ro + 3.0 * gap:
            return False

        # Require spot to be stable enough to justify restart overhead.
        avg_on_sec = max(gap, self._avg_on_steps * gap)
        if avg_on_sec < 1.2 * ro + 2.0 * gap:
            return False

        # Require a short confirmation streak (prevents thrashing on 1-step blips).
        if self._spot_streak < self._min_spot_confirm:
            return False

        return True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_initialized()

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        done = self._sum_done_time()
        if self._last_elapsed is not None and self._last_done is not None and self._last_action is not None:
            # Update streak stats and average on-duration from the spot availability signal.
            if self._last_has_spot is not None:
                if self._last_has_spot and (not has_spot):
                    ended = max(1, int(self._prev_spot_streak))
                    self._avg_on_steps = (1.0 - self._avg_on_alpha) * self._avg_on_steps + self._avg_on_alpha * float(ended)

        # Update observation statistics with current availability.
        self._steps_obs += 1
        if has_spot:
            self._spot_obs += 1

        # Update current streak counters.
        if has_spot:
            self._spot_streak += 1
        else:
            self._prev_spot_streak = self._spot_streak
            self._spot_streak = 0

        # Decrement OD hold.
        if self._od_hold_steps > 0:
            self._od_hold_steps -= 1

        remaining_work = max(0.0, task_duration - done)
        remaining_time = max(0.0, deadline - elapsed)

        # Record last state for next update.
        if self._last_elapsed is None:
            self._last_elapsed = elapsed
            self._last_done = done
            self._last_action = last_cluster_type
            self._last_has_spot = has_spot
        else:
            self._last_elapsed = elapsed
            self._last_done = done
            self._last_action = last_cluster_type
            self._last_has_spot = has_spot

        if remaining_work <= 0.0:
            return ClusterType.NONE

        if remaining_time <= 0.0:
            return ClusterType.NONE

        # If time is tight, commit to on-demand to guarantee completion.
        if self._time_tight(remaining_time, remaining_work):
            self._od_hold_steps = max(self._od_hold_steps, self._min_od_hold)
            return ClusterType.ON_DEMAND

        p_spot_low = self._estimate_p_spot_low()
        spot_eff = self._spot_efficiency()

        # Expected effective spot work capacity over remaining time (conservative).
        effective_spot_work = p_spot_low * spot_eff * remaining_time
        od_needed = max(0.0, remaining_work - effective_spot_work)
        nonspot_time_est = (1.0 - p_spot_low) * remaining_time

        # If we need more OD work than expected nonspot time, we should run OD even during spot windows.
        od_almost_always = od_needed >= max(0.0, nonspot_time_est - (1.5 * ro + 2.0 * gap))

        if has_spot:
            if od_almost_always:
                # Still avoid switching away from OD if already on it; otherwise use spot.
                if last_cluster_type == ClusterType.ON_DEMAND:
                    self._od_hold_steps = max(self._od_hold_steps, self._min_od_hold)
                    return ClusterType.ON_DEMAND
                return ClusterType.SPOT

            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT

            if last_cluster_type == ClusterType.ON_DEMAND:
                if self._od_hold_steps > 0:
                    self._od_hold_steps = max(self._od_hold_steps, self._min_od_hold)
                    return ClusterType.ON_DEMAND
                if self._should_switch_od_to_spot(remaining_time, remaining_work):
                    return ClusterType.SPOT
                self._od_hold_steps = max(self._od_hold_steps, self._min_od_hold)
                return ClusterType.ON_DEMAND

            return ClusterType.SPOT

        # No spot available.
        if last_cluster_type == ClusterType.ON_DEMAND and self._od_hold_steps > 0:
            self._od_hold_steps = max(self._od_hold_steps, self._min_od_hold)
            return ClusterType.ON_DEMAND

        # Decide whether we must use this non-spot window for OD.
        # If skipping this step would force OD into spot windows later, run OD now.
        margin = 2.0 * ro + 2.0 * gap
        must_use_nonspot_for_od = od_needed > max(0.0, nonspot_time_est - margin)

        if must_use_nonspot_for_od:
            self._od_hold_steps = max(self._od_hold_steps, self._min_od_hold)
            return ClusterType.ON_DEMAND

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)