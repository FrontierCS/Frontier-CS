from __future__ import annotations

import json
from typing import Any, Optional


try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:  # pragma: no cover
    class Strategy:  # minimal fallback
        def __init__(self, *args, **kwargs):
            self.env = None

    class ClusterType:
        SPOT = "SPOT"
        ON_DEMAND = "ON_DEMAND"
        NONE = "NONE"


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self.args = args

        self._last_has_spot: Optional[bool] = None
        self._steps: int = 0
        self._seen_seconds: float = 0.0
        self._transition_count: int = 0

        self._spot_avail_run: float = 0.0
        self._spot_unavail_run: float = 0.0

        self._ema_avail_run: float = 3600.0  # initial guess: 1 hour
        self._ema_unavail_run: float = 900.0  # initial guess: 15 min
        self._ema_alpha: float = 0.2

        self._force_od_latched: bool = False
        self._od_hold_until: float = 0.0

        self._prev_work_done: float = 0.0
        self._prev_elapsed: float = 0.0

        self._spec: dict[str, Any] = {}

    def solve(self, spec_path: str) -> "Solution":
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                txt = f.read().strip()
            if txt:
                try:
                    self._spec = json.loads(txt)
                except Exception:
                    self._spec = {}
        except Exception:
            self._spec = {}
        return self

    def _get_work_done(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0

        if isinstance(td, (int, float)):
            return float(td)

        if not isinstance(td, (list, tuple)) or not td:
            return 0.0

        # Common cases:
        # 1) list of segment durations (seconds): sum(list)
        # 2) list of tuples (start, end): sum(end-start)
        # 3) list of cumulative progress values: last
        s = 0.0
        numeric_list = True
        vals = []
        for seg in td:
            if seg is None:
                continue
            if isinstance(seg, (int, float)):
                v = float(seg)
                vals.append(v)
                s += v
            elif isinstance(seg, (list, tuple)) and len(seg) == 2 and isinstance(seg[0], (int, float)) and isinstance(seg[1], (int, float)):
                numeric_list = False
                a = float(seg[0])
                b = float(seg[1])
                if b > a:
                    s += (b - a)
            elif isinstance(seg, dict):
                numeric_list = False
                if "duration" in seg and isinstance(seg["duration"], (int, float)):
                    s += float(seg["duration"])
                elif "start" in seg and "end" in seg and isinstance(seg["start"], (int, float)) and isinstance(seg["end"], (int, float)):
                    a = float(seg["start"])
                    b = float(seg["end"])
                    if b > a:
                        s += (b - a)
                elif "done" in seg and isinstance(seg["done"], (int, float)):
                    s += float(seg["done"])
            else:
                numeric_list = False

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        if numeric_list and vals:
            if s <= task_duration + 1e-6:
                return s
            # If values look monotonic, treat as cumulative and use last.
            mono = True
            for i in range(len(vals) - 1):
                if vals[i] > vals[i + 1] + 1e-9:
                    mono = False
                    break
            if mono:
                return min(vals[-1], task_duration if task_duration > 0 else vals[-1])
            return min(s, task_duration if task_duration > 0 else s)

        if task_duration > 0:
            return min(s, task_duration)
        return s

    def _update_spot_stats(self, has_spot: bool, gap: float) -> None:
        if self._last_has_spot is None:
            self._last_has_spot = has_spot
            if has_spot:
                self._spot_avail_run = gap
                self._spot_unavail_run = 0.0
            else:
                self._spot_unavail_run = gap
                self._spot_avail_run = 0.0
            return

        if has_spot == self._last_has_spot:
            if has_spot:
                self._spot_avail_run += gap
            else:
                self._spot_unavail_run += gap
            return

        # Transition
        self._transition_count += 1
        if self._last_has_spot:
            # avail run ended
            ended = self._spot_avail_run
            if ended > 0:
                self._ema_avail_run = self._ema_alpha * ended + (1.0 - self._ema_alpha) * self._ema_avail_run
        else:
            ended = self._spot_unavail_run
            if ended > 0:
                self._ema_unavail_run = self._ema_alpha * ended + (1.0 - self._ema_alpha) * self._ema_unavail_run

        self._last_has_spot = has_spot
        if has_spot:
            self._spot_avail_run = gap
            self._spot_unavail_run = 0.0
        else:
            self._spot_unavail_run = gap
            self._spot_avail_run = 0.0

    def _estimate_critical_buffer(self, time_to_deadline: float, gap: float) -> float:
        restart = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        # Estimate toggling rate from observed availability transitions.
        observed_rate = float(self._transition_count) / max(self._seen_seconds, gap, 1.0)
        default_rate = 1.0 / 7200.0  # 1 toggle per 2 hours prior
        rate = 0.7 * observed_rate + 0.3 * default_rate

        expected_transitions = rate * max(time_to_deadline, 0.0)
        expected_overhead = expected_transitions * restart * 0.6
        expected_overhead = min(expected_overhead, 0.30 * time_to_deadline)

        return expected_overhead + 2.5 * restart + 2.0 * gap

    def _spot_switch_stable_time(self, slack: float, remaining_work: float) -> float:
        base = 900.0  # 15 min
        if self._ema_avail_run > 2.0 * 3600.0:
            base = 600.0
        elif self._ema_avail_run < 1800.0:
            base = 1200.0

        if slack < 3600.0:
            base += 600.0
        elif slack > 3.0 * 3600.0:
            base = max(300.0, base - 300.0)

        if remaining_work < 2.0 * 3600.0:
            base += 600.0

        if base < 300.0:
            base = 300.0
        if base > 2400.0:
            base = 2400.0
        return base

    def _wait_time_during_outage(self, slack: float, gap: float) -> float:
        restart = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        if slack <= 0.0:
            return 0.0

        base = 0.25 * self._ema_unavail_run
        if base < 120.0:
            base = 120.0
        if base > 1200.0:
            base = 1200.0

        if slack > 3.0 * 3600.0:
            base *= 1.5
        elif slack < 3600.0:
            base *= 0.5

        if base > 1800.0:
            base = 1800.0

        guard = restart + 2.0 * gap
        max_wait = slack - guard
        if max_wait <= 0.0:
            return 0.0

        if base > max_wait:
            base = max_wait
        return max(0.0, base)

    def _od_hold_time(self, slack: float) -> float:
        hold = 900.0  # 15 min
        if self._ema_avail_run < 3600.0:
            hold = 1800.0
        if slack < 2.0 * 3600.0:
            hold = max(hold, 1800.0)
        return hold

    def _in_restart_overhead(self, last_cluster_type: ClusterType, delta_work: float, gap: float, remaining_work: float) -> bool:
        if remaining_work <= 0:
            return False
        if last_cluster_type == ClusterType.NONE:
            return False
        # If we are "running" but progress barely moved, we likely are burning restart overhead.
        return delta_work < 0.20 * gap

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        t = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)

        self._steps += 1
        self._seen_seconds = max(self._seen_seconds, (self._steps * gap) if gap > 0 else t)

        self._update_spot_stats(has_spot, gap)

        work_done = self._get_work_done()
        remaining_work = float(getattr(self, "task_duration", 0.0) or 0.0) - work_done
        if remaining_work <= 0.0:
            self._prev_work_done = work_done
            self._prev_elapsed = t
            return ClusterType.NONE

        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        time_to_deadline = deadline - t
        if time_to_deadline <= 0.0:
            self._prev_work_done = work_done
            self._prev_elapsed = t
            return ClusterType.NONE

        slack = time_to_deadline - remaining_work

        delta_work = work_done - self._prev_work_done
        self._prev_work_done = work_done
        self._prev_elapsed = t

        if slack < 0.0:
            self._force_od_latched = True

        crit_buf = self._estimate_critical_buffer(time_to_deadline, gap)
        if slack <= crit_buf:
            self._force_od_latched = True

        if self._force_od_latched:
            if not (last_cluster_type == ClusterType.ON_DEMAND):
                self._od_hold_until = max(self._od_hold_until, t + self._od_hold_time(slack))
            return ClusterType.ON_DEMAND

        # If we appear to be currently consuming restart overhead, don't switch unless forced.
        if self._in_restart_overhead(last_cluster_type, delta_work, gap, remaining_work):
            if last_cluster_type == ClusterType.SPOT and not has_spot:
                pass
            else:
                return last_cluster_type

        if last_cluster_type == ClusterType.SPOT:
            if has_spot:
                return ClusterType.SPOT
            # spot unavailable: optionally wait a bit to avoid OD + another switch if outage is short
            wait = self._wait_time_during_outage(slack, gap)
            if self._spot_unavail_run < wait:
                return ClusterType.NONE
            self._od_hold_until = max(self._od_hold_until, t + self._od_hold_time(slack))
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.ON_DEMAND:
            if not has_spot:
                return ClusterType.ON_DEMAND
            if t < self._od_hold_until:
                return ClusterType.ON_DEMAND
            stable = self._spot_switch_stable_time(slack, remaining_work)
            restart = float(getattr(self, "restart_overhead", 0.0) or 0.0)
            if self._spot_avail_run >= stable and slack > (1.5 * restart + gap):
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # last_cluster_type == NONE (or unknown)
        if has_spot:
            restart = float(getattr(self, "restart_overhead", 0.0) or 0.0)
            if slack <= 0.5 * restart:
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        wait = self._wait_time_during_outage(slack, gap)
        if self._spot_unavail_run < wait:
            return ClusterType.NONE
        self._od_hold_until = max(self._od_hold_until, t + self._od_hold_time(slack))
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
