import argparse
import json
import math
import os
from typing import Any, Iterable, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass
        self._reset_internal_state()

    def _reset_internal_state(self) -> None:
        self._params_ready = False
        self._total_steps = 0
        self._spot_steps = 0

        self._spot_streak = 0
        self._no_spot_streak = 0
        self._in_spot_run = False
        self._in_no_spot_run = False
        self._spot_runs = 0
        self._no_spot_runs = 0
        self._avg_spot_run_steps = 0.0
        self._avg_no_spot_run_steps = 0.0

        self._task_done_cache_key = None
        self._task_done_cache_val = 0.0

        self._od_started = False
        self._od_lock = False

        self._overhead_steps = 0
        self._min_spot_streak_to_switch = 2
        self._lock_slack_seconds = 0.0
        self._switch_slack_seconds = 0.0

        self._spec = {}

    def solve(self, spec_path: str) -> "Solution":
        self._reset_internal_state()
        if spec_path and os.path.exists(spec_path):
            try:
                with open(spec_path, "r", encoding="utf-8") as f:
                    self._spec = json.load(f)
            except Exception:
                self._spec = {}
        return self

    def _ensure_params(self) -> None:
        if self._params_ready:
            return
        gap = float(getattr(getattr(self, "env", None), "gap_seconds", 60.0) or 60.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        if overhead > 0.0 and gap > 0.0:
            self._overhead_steps = int(math.ceil(overhead / gap))
        else:
            self._overhead_steps = 0

        self._min_spot_streak_to_switch = max(2, min(6, self._overhead_steps + 1))
        self._lock_slack_seconds = max(2.0 * overhead, 0.0) + max(0.5 * gap, 0.0)
        self._switch_slack_seconds = (self._overhead_steps + 1) * overhead + gap

        self._params_ready = True

    @staticmethod
    def _sum_done_segments(val: Any) -> float:
        if val is None:
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, dict):
            total = 0.0
            for v in val.values():
                total += Solution._sum_done_segments(v)
            return total
        if isinstance(val, (list, tuple)):
            total = 0.0
            for x in val:
                if x is None:
                    continue
                if isinstance(x, (int, float)):
                    total += float(x)
                elif isinstance(x, (list, tuple)) and len(x) >= 2 and isinstance(x[0], (int, float)) and isinstance(
                    x[1], (int, float)
                ):
                    total += float(x[1]) - float(x[0])
                else:
                    total += Solution._sum_done_segments(x)
            return total
        return 0.0

    def _done_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        key = None
        if isinstance(tdt, list):
            last = tdt[-1] if tdt else None
            key = ("list", id(tdt), len(tdt), repr(last)[:64])
        elif isinstance(tdt, tuple):
            last = tdt[-1] if tdt else None
            key = ("tuple", id(tdt), len(tdt), repr(last)[:64])
        else:
            key = ("other", repr(tdt)[:128])

        if key == self._task_done_cache_key:
            return self._task_done_cache_val

        done = float(self._sum_done_segments(tdt))
        if done < 0.0:
            done = 0.0
        self._task_done_cache_key = key
        self._task_done_cache_val = done
        return done

    def _update_run_stats(self, has_spot: bool) -> None:
        if has_spot:
            if not self._in_spot_run:
                if self._in_no_spot_run:
                    self._no_spot_runs += 1
                    if self._no_spot_runs == 1:
                        self._avg_no_spot_run_steps = float(self._no_spot_streak)
                    else:
                        self._avg_no_spot_run_steps += (float(self._no_spot_streak) - self._avg_no_spot_run_steps) / float(
                            self._no_spot_runs
                        )
                self._spot_streak = 1
                self._no_spot_streak = 0
                self._in_spot_run = True
                self._in_no_spot_run = False
            else:
                self._spot_streak += 1
                self._no_spot_streak = 0
        else:
            if not self._in_no_spot_run:
                if self._in_spot_run:
                    self._spot_runs += 1
                    if self._spot_runs == 1:
                        self._avg_spot_run_steps = float(self._spot_streak)
                    else:
                        self._avg_spot_run_steps += (float(self._spot_streak) - self._avg_spot_run_steps) / float(
                            self._spot_runs
                        )
                self._no_spot_streak = 1
                self._spot_streak = 0
                self._in_no_spot_run = True
                self._in_spot_run = False
            else:
                self._no_spot_streak += 1
                self._spot_streak = 0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_params()

        self._total_steps += 1
        if has_spot:
            self._spot_steps += 1
        self._update_run_stats(has_spot)

        env = getattr(self, "env", None)
        elapsed = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(env, "gap_seconds", 60.0) or 60.0)

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        done = self._done_seconds()
        remaining = task_duration - done
        if remaining <= 1e-9:
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 1e-9:
            return ClusterType.NONE

        slack = time_left - remaining
        if slack <= self._lock_slack_seconds:
            self._od_lock = True

        if self._od_lock:
            self._od_started = True
            return ClusterType.ON_DEMAND

        if not has_spot:
            if self._od_started:
                return ClusterType.ON_DEMAND

            feasible_after_idle = remaining <= (time_left - gap - overhead)
            if feasible_after_idle:
                return ClusterType.NONE

            self._od_started = True
            return ClusterType.ON_DEMAND

        if self._od_started and last_cluster_type == ClusterType.ON_DEMAND:
            if self._spot_streak >= self._min_spot_streak_to_switch and slack >= self._switch_slack_seconds:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
