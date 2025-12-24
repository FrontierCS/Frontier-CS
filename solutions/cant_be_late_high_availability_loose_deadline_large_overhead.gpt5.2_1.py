import math
from typing import Any, Optional

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

        self._last_elapsed: Optional[float] = None
        self._prev_has_spot: Optional[bool] = None

        self._ema_p: float = 0.65
        self._ema_alpha: float = 0.03

        self._spot_streak_steps: int = 0
        self._no_spot_streak_steps: int = 0

        self._done_cache_seconds: float = 0.0
        self._done_cache_len: int = 0
        self._done_cache_is_list: bool = False

        self._consec_spot_steps: int = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _is_number(x: Any) -> bool:
        return isinstance(x, (int, float)) and not isinstance(x, bool)

    def _seg_to_seconds(self, seg: Any) -> float:
        if seg is None:
            return 0.0
        if self._is_number(seg):
            v = float(seg)
            return v if v > 0 else 0.0
        if isinstance(seg, dict):
            if "duration" in seg and self._is_number(seg["duration"]):
                v = float(seg["duration"])
                return v if v > 0 else 0.0
            if "start" in seg and "end" in seg and self._is_number(seg["start"]) and self._is_number(seg["end"]):
                v = float(seg["end"]) - float(seg["start"])
                return v if v > 0 else 0.0
            if "work" in seg and self._is_number(seg["work"]):
                v = float(seg["work"])
                return v if v > 0 else 0.0
            return 0.0
        if isinstance(seg, (tuple, list)) and len(seg) >= 2 and self._is_number(seg[0]) and self._is_number(seg[1]):
            a = float(seg[0])
            b = float(seg[1])
            v = b - a
            if v > 0:
                return v
            v2 = b if b > 0 else 0.0
            return v2
        duration = getattr(seg, "duration", None)
        if self._is_number(duration):
            v = float(duration)
            return v if v > 0 else 0.0
        start = getattr(seg, "start", None)
        end = getattr(seg, "end", None)
        if self._is_number(start) and self._is_number(end):
            v = float(end) - float(start)
            return v if v > 0 else 0.0
        return 0.0

    def _recompute_done_seconds_full(self) -> float:
        t = getattr(self, "task_done_time", None)
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)

        if t is None:
            return 0.0

        if self._is_number(t):
            done = float(t)
            if done < 0:
                done = 0.0
            done = min(done, task_duration if task_duration > 0 else done)
            done = min(done, elapsed if elapsed > 0 else done)
            return done

        if isinstance(t, list):
            nums_only = True
            vals = []
            for seg in t:
                if self._is_number(seg):
                    vals.append(float(seg))
                else:
                    nums_only = False
                    break

            if nums_only and vals:
                nondecreasing = True
                last = vals[0]
                for v in vals[1:]:
                    if v + 1e-9 < last:
                        nondecreasing = False
                        break
                    last = v
                s = sum(v for v in vals if v > 0)
                m = max(vals)
                if task_duration > 0:
                    s_ok = s <= task_duration * 1.15 + 1e-6
                    m_ok = 0.0 <= m <= task_duration * 1.15 + 1e-6
                else:
                    s_ok = True
                    m_ok = True

                if elapsed > 0:
                    s_ok = s_ok and s <= elapsed + 1e-6
                    m_ok = m_ok and m <= elapsed + 1e-6

                if s_ok:
                    done = s
                elif nondecreasing and m_ok:
                    done = m
                else:
                    done = min(s, m) if m_ok else (s if s_ok else 0.0)

                if done < 0:
                    done = 0.0
                if task_duration > 0:
                    done = min(done, task_duration)
                if elapsed > 0:
                    done = min(done, elapsed)
                return done

            total = 0.0
            for seg in t:
                total += self._seg_to_seconds(seg)
            if total < 0:
                total = 0.0
            if task_duration > 0:
                total = min(total, task_duration)
            if elapsed > 0:
                total = min(total, elapsed)
            return total

        return 0.0

    def _get_done_seconds(self) -> float:
        t = getattr(self, "task_done_time", None)
        if isinstance(t, list):
            if not self._done_cache_is_list:
                self._done_cache_is_list = True
                self._done_cache_len = 0
                self._done_cache_seconds = 0.0

            cur_len = len(t)
            if cur_len < self._done_cache_len:
                done = self._recompute_done_seconds_full()
                self._done_cache_seconds = done
                self._done_cache_len = cur_len
                return done

            if cur_len == self._done_cache_len:
                return self._done_cache_seconds

            add = 0.0
            for i in range(self._done_cache_len, cur_len):
                add += self._seg_to_seconds(t[i])
            self._done_cache_seconds += add
            self._done_cache_len = cur_len

            elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
            task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
            done = self._done_cache_seconds
            if done < 0:
                done = 0.0
            if task_duration > 0:
                done = min(done, task_duration)
            if elapsed > 0:
                done = min(done, elapsed)
            self._done_cache_seconds = done
            return done

        self._done_cache_is_list = False
        self._done_cache_len = 0
        self._done_cache_seconds = 0.0
        return self._recompute_done_seconds_full()

    def _reset_episode(self):
        self._last_elapsed = None
        self._prev_has_spot = None
        self._ema_p = 0.65
        self._spot_streak_steps = 0
        self._no_spot_streak_steps = 0
        self._done_cache_seconds = 0.0
        self._done_cache_len = 0
        self._done_cache_is_list = False
        self._consec_spot_steps = 0

    def _update_availability_stats(self, has_spot: bool, gap: float):
        x = 1.0 if has_spot else 0.0
        a = self._ema_alpha
        self._ema_p = (1.0 - a) * self._ema_p + a * x
        if self._ema_p < 0.02:
            self._ema_p = 0.02
        elif self._ema_p > 0.98:
            self._ema_p = 0.98

        if self._prev_has_spot is None:
            self._prev_has_spot = has_spot
            if has_spot:
                self._spot_streak_steps = 1
                self._no_spot_streak_steps = 0
                self._consec_spot_steps = 1
            else:
                self._spot_streak_steps = 0
                self._no_spot_streak_steps = 1
                self._consec_spot_steps = 0
            return

        if has_spot == self._prev_has_spot:
            if has_spot:
                self._spot_streak_steps += 1
                self._consec_spot_steps += 1
            else:
                self._no_spot_streak_steps += 1
                self._consec_spot_steps = 0
        else:
            self._prev_has_spot = has_spot
            if has_spot:
                self._spot_streak_steps = 1
                self._no_spot_streak_steps = 0
                self._consec_spot_steps = 1
            else:
                self._no_spot_streak_steps = 1
                self._spot_streak_steps = 0
                self._consec_spot_steps = 0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if gap <= 0:
            gap = 1.0

        if self._last_elapsed is None:
            self._last_elapsed = elapsed
        else:
            if elapsed + 1e-9 < self._last_elapsed or (elapsed <= 1e-9 and self._last_elapsed > 1e-9):
                self._reset_episode()
                self._last_elapsed = elapsed
            else:
                self._last_elapsed = elapsed

        self._update_availability_stats(has_spot, gap)

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        restart = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        if restart < 0:
            restart = 0.0

        done = self._get_done_seconds()
        remaining_work = task_duration - done
        if remaining_work <= 0:
            return ClusterType.NONE

        remaining_time = deadline - elapsed
        if remaining_time <= 0:
            return ClusterType.ON_DEMAND

        slack = remaining_time - remaining_work

        commit_guard = max(3.0 * restart + 2.0 * gap, 4.0 * gap, 900.0)
        idle_guard = commit_guard + max(restart, gap, 0.0)
        switch_guard = max(2.0 * restart + gap, 3.0 * gap, 600.0)

        confirm_steps = 1 if restart <= 0.5 * gap else 2

        if slack <= commit_guard:
            return ClusterType.ON_DEMAND

        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                if self._consec_spot_steps < confirm_steps:
                    return ClusterType.ON_DEMAND
                if slack <= switch_guard:
                    return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        if slack > idle_guard:
            return ClusterType.NONE
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
