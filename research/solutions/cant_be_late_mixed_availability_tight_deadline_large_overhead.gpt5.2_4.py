import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._committed_od = False
        self._last_elapsed_obs: Optional[float] = None
        self._last_done_obs: float = 0.0

        self._avail_ewma: float = 0.6
        self._spot_avail_streak: int = 0
        self._spot_unavail_streak: int = 0

        self._spot_progressing: bool = True

        self._done_est: float = 0.0

    def solve(self, spec_path: str) -> "Solution":
        self._reset_internal()
        return self

    def _reset_internal(self) -> None:
        self._committed_od = False
        self._last_elapsed_obs = None
        self._last_done_obs = 0.0

        self._avail_ewma = 0.6
        self._spot_avail_streak = 0
        self._spot_unavail_streak = 0
        self._spot_progressing = True
        self._done_est = 0.0

    def _completed_work_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        td = float(getattr(self, "task_duration", 0.0) or 0.0)

        if tdt is None:
            return max(0.0, min(self._done_est, td))

        if isinstance(tdt, (int, float)):
            done = float(tdt)
            done = max(0.0, min(done, td))
            self._done_est = done
            return done

        if not isinstance(tdt, (list, tuple)) or len(tdt) == 0:
            return max(0.0, min(self._done_est, td))

        first = tdt[0]
        done = 0.0

        if isinstance(first, (int, float)):
            monotonic = True
            prev = float(first)
            for x in tdt[1:]:
                if not isinstance(x, (int, float)):
                    monotonic = False
                    break
                fx = float(x)
                if fx + 1e-9 < prev:
                    monotonic = False
                    break
                prev = fx

            if monotonic and prev <= td * 1.1:
                done = prev
            else:
                s = 0.0
                for x in tdt:
                    if isinstance(x, (int, float)):
                        s += float(x)
                done = s
        else:
            s = 0.0
            best_cum = None
            for seg in tdt:
                if isinstance(seg, dict):
                    if "done" in seg and isinstance(seg["done"], (int, float)):
                        v = float(seg["done"])
                        best_cum = v if best_cum is None else max(best_cum, v)
                    elif "duration" in seg and isinstance(seg["duration"], (int, float)):
                        s += float(seg["duration"])
                elif isinstance(seg, (list, tuple)) and len(seg) >= 2 and isinstance(seg[0], (int, float)) and isinstance(seg[1], (int, float)):
                    a = float(seg[0])
                    b = float(seg[1])
                    if b >= a:
                        s += (b - a)
                    else:
                        s += (a - b)
                elif isinstance(seg, (int, float)):
                    s += float(seg)

            done = float(best_cum) if best_cum is not None else s

        done = max(0.0, min(done, td))
        self._done_est = done
        return done

    def _safety_buffer_seconds(self, gap: float) -> float:
        over = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        a = float(self._avail_ewma)

        base = gap + 0.2 * over + 60.0
        risk = (1.0 - a) * 0.8 * over
        safety = base + risk

        if safety < gap:
            safety = gap
        return safety

    def _spot_confirm_steps(self, gap: float) -> int:
        if gap <= 0:
            return 1
        over = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        if over <= 0:
            return 1

        steps_over = int(math.ceil(over / gap))
        if steps_over <= 1:
            return 1

        a = self._avail_ewma
        if a >= 0.7:
            return 1

        base = int(math.ceil(over / (2.0 * gap)))
        if a < 0.35:
            base = min(steps_over, base + 1)
        if a < 0.2:
            base = min(steps_over, base + 1)

        base = max(1, min(base, 6))
        return base

    def _maybe_reset_episode(self, elapsed: float) -> None:
        if self._last_elapsed_obs is None:
            return
        if elapsed + 1e-9 < self._last_elapsed_obs:
            self._reset_internal()

    def _update_availability_stats(self, has_spot: bool) -> None:
        alpha = 0.05
        x = 1.0 if has_spot else 0.0
        self._avail_ewma = alpha * x + (1.0 - alpha) * self._avail_ewma

        if has_spot:
            self._spot_avail_streak += 1
            self._spot_unavail_streak = 0
        else:
            self._spot_unavail_streak += 1
            self._spot_avail_streak = 0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)

        self._maybe_reset_episode(elapsed)
        self._update_availability_stats(has_spot)

        done = self._completed_work_seconds()
        remaining = float(getattr(self, "task_duration", 0.0) or 0.0) - done
        if remaining <= 1e-6:
            self._last_elapsed_obs = elapsed
            self._last_done_obs = done
            return ClusterType.NONE

        # Infer whether spot was progressing during the previous step.
        if self._last_elapsed_obs is not None and elapsed > self._last_elapsed_obs + 1e-9:
            delta_done = done - self._last_done_obs
            if last_cluster_type == ClusterType.SPOT:
                self._spot_progressing = delta_done > 1e-9
            elif last_cluster_type == ClusterType.ON_DEMAND:
                self._spot_progressing = False

        if last_cluster_type == ClusterType.ON_DEMAND:
            self._committed_od = True

        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        time_left = deadline - elapsed

        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        safety = self._safety_buffer_seconds(gap)

        if self._committed_od:
            self._last_elapsed_obs = elapsed
            self._last_done_obs = done
            return ClusterType.ON_DEMAND

        overhead_now = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead
        if time_left <= remaining + overhead_now + safety:
            self._committed_od = True
            self._last_elapsed_obs = elapsed
            self._last_done_obs = done
            return ClusterType.ON_DEMAND

        # Decide default action (before feasibility check)
        if has_spot:
            if last_cluster_type != ClusterType.SPOT:
                confirm_steps = self._spot_confirm_steps(gap)
                if self._spot_avail_streak < confirm_steps:
                    candidate = ClusterType.NONE
                else:
                    candidate = ClusterType.SPOT
            else:
                candidate = ClusterType.SPOT
        else:
            candidate = ClusterType.NONE

        # One-step lookahead feasibility (assume conservative progress when starting/uncertain)
        if gap > 0.0:
            time_left_after = time_left - gap
            if candidate == ClusterType.SPOT:
                # If we were already progressing on spot, assume we get a full step of progress;
                # otherwise assume 0 progress (e.g., still in restart overhead).
                progress_est = gap if (last_cluster_type == ClusterType.SPOT and self._spot_progressing) else 0.0
                remaining_after = remaining - progress_est
                if remaining_after < 0.0:
                    remaining_after = 0.0
                if time_left_after <= remaining_after + restart_overhead + safety:
                    self._committed_od = True
                    self._last_elapsed_obs = elapsed
                    self._last_done_obs = done
                    return ClusterType.ON_DEMAND
            else:
                # NONE: no progress
                if time_left_after <= remaining + restart_overhead + safety:
                    self._committed_od = True
                    self._last_elapsed_obs = elapsed
                    self._last_done_obs = done
                    return ClusterType.ON_DEMAND

        # Return candidate (must respect has_spot constraint)
        if candidate == ClusterType.SPOT and not has_spot:
            candidate = ClusterType.NONE

        self._last_elapsed_obs = elapsed
        self._last_done_obs = done
        return candidate

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)