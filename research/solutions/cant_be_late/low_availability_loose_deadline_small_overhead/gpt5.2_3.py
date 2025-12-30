from __future__ import annotations

import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "slack_then_commit_v3"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self._reset_episode_state()

    def _reset_episode_state(self) -> None:
        self._committed = False
        self._step_count = 0
        self._spot_available_steps = 0
        self._last_has_spot: Optional[bool] = None
        self._current_spot_run = 0
        self._ema_spot_run: Optional[float] = None
        self._last_elapsed: Optional[float] = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _maybe_reset_for_new_episode(self, elapsed: float) -> None:
        if self._last_elapsed is None:
            self._last_elapsed = elapsed
            return
        if elapsed + 1e-9 < self._last_elapsed:
            self._reset_episode_state()
            self._last_elapsed = elapsed
            return
        if elapsed <= 1e-9 and self._step_count > 0:
            self._reset_episode_state()
            self._last_elapsed = elapsed
            return
        self._last_elapsed = elapsed

    def _update_spot_stats(self, has_spot: bool) -> None:
        self._step_count += 1
        if has_spot:
            self._spot_available_steps += 1

        if self._last_has_spot is None:
            self._last_has_spot = has_spot
            self._current_spot_run = 1 if has_spot else 0
            return

        if has_spot:
            if self._last_has_spot:
                self._current_spot_run += 1
            else:
                self._current_spot_run = 1
        else:
            if self._last_has_spot:
                run = int(self._current_spot_run)
                if run > 0:
                    if self._ema_spot_run is None:
                        self._ema_spot_run = float(run)
                    else:
                        self._ema_spot_run = 0.85 * self._ema_spot_run + 0.15 * float(run)
            self._current_spot_run = 0

        self._last_has_spot = has_spot

    def _get_done_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if not td:
            return 0.0

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        gap = float(getattr(getattr(self, "env", None), "gap_seconds", 0.0) or 0.0)

        try:
            first = td[0]
        except Exception:
            return 0.0

        if isinstance(first, (tuple, list)) and len(first) == 2:
            total = 0.0
            for seg in td:
                if isinstance(seg, (tuple, list)) and len(seg) == 2:
                    try:
                        a = float(seg[0])
                        b = float(seg[1])
                    except Exception:
                        continue
                    if b > a:
                        total += (b - a)
            if task_duration > 0.0:
                return max(0.0, min(task_duration, total))
            return max(0.0, total)

        vals = []
        for v in td:
            try:
                vals.append(float(v))
            except Exception:
                continue
        if not vals:
            return 0.0

        nondec = True
        for i in range(len(vals) - 1):
            if vals[i + 1] + 1e-9 < vals[i]:
                nondec = False
                break

        last = vals[-1]
        s = float(sum(vals))

        if nondec and len(vals) >= 2:
            if gap > 0.0:
                if last > 3.0 * gap and (task_duration <= 0.0 or last <= task_duration + 1e-6):
                    done = last
                    if task_duration > 0.0:
                        done = min(done, task_duration)
                    return max(0.0, done)
            else:
                avg_delta = (vals[-1] - vals[0]) / max(1, (len(vals) - 1))
                if avg_delta > 0.0 and (task_duration <= 0.0 or last <= task_duration + 1e-6):
                    done = last
                    if task_duration > 0.0:
                        done = min(done, task_duration)
                    return max(0.0, done)

        if task_duration > 0.0:
            return max(0.0, min(task_duration, s))
        return max(0.0, s)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = float(getattr(getattr(self, "env", None), "elapsed_seconds", 0.0) or 0.0)
        self._maybe_reset_for_new_episode(elapsed)
        self._update_spot_stats(has_spot)

        gap = float(getattr(getattr(self, "env", None), "gap_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        time_left = deadline - elapsed
        if time_left <= 0.0:
            return ClusterType.NONE

        done = self._get_done_seconds()
        remaining = task_duration - done
        if remaining <= 1e-6:
            return ClusterType.NONE

        slack = time_left - remaining

        base_min = max(3600.0, 12.0 * overhead, 6.0 * gap)
        s_min = min(base_min, 6.0 * 3600.0)
        s_tight = max(3.0 * overhead, 3.0 * gap, 300.0)

        hard_panic = time_left <= remaining + max(4.0 * overhead, 4.0 * gap, 600.0)
        if hard_panic:
            return ClusterType.ON_DEMAND

        if not self._committed and slack <= s_min:
            self._committed = True

        if not self._committed:
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.NONE

        if slack <= s_tight:
            return ClusterType.ON_DEMAND

        if has_spot:
            confirm = 1
            if self._ema_spot_run is not None and self._ema_spot_run < 2.0:
                confirm = 2
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            if confirm <= 1 or self._current_spot_run >= confirm:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)