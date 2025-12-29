import argparse
import json
import os
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_slack_v1"

    def __init__(self, args: Optional[argparse.Namespace] = None):
        try:
            super().__init__(args)
        except TypeError:
            super().__init__()
        self.args = args

        self._phase = 1  # 1: idle-on-outage, 2: od-on-outage, 3: od-only
        self._spot_streak = 0
        self._no_spot_streak = 0
        self._min_spot_confirm_steps = 2

        self._cfg = {}

    def solve(self, spec_path: str) -> "Solution":
        cfg = {}
        if spec_path and os.path.exists(spec_path):
            try:
                with open(spec_path, "r", encoding="utf-8") as f:
                    txt = f.read()
                try:
                    cfg = json.loads(txt)
                except Exception:
                    cfg = {}
            except Exception:
                cfg = {}
        self._cfg = cfg or {}
        v = self._cfg.get("min_spot_confirm_steps")
        if isinstance(v, int) and v >= 1:
            self._min_spot_confirm_steps = v
        return self

    def _done_seconds(self) -> float:
        segs = getattr(self, "task_done_time", None)
        if not segs:
            return 0.0
        total = 0.0
        for seg in segs:
            if isinstance(seg, (int, float)):
                total += float(seg)
            elif isinstance(seg, (list, tuple)) and len(seg) >= 2:
                try:
                    total += float(seg[1]) - float(seg[0])
                except Exception:
                    try:
                        total += float(seg[0])
                    except Exception:
                        pass
            else:
                try:
                    total += float(seg)
                except Exception:
                    pass
        if total < 0:
            return 0.0
        return total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if has_spot:
            self._spot_streak += 1
            self._no_spot_streak = 0
        else:
            self._no_spot_streak += 1
            self._spot_streak = 0

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 60.0))
        deadline = float(getattr(self, "deadline", 0.0))
        task_duration = float(getattr(self, "task_duration", 0.0))
        overhead = float(getattr(self, "restart_overhead", 0.0))

        done = self._done_seconds()
        remaining = task_duration - done
        if remaining <= 0.0:
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0.0:
            return ClusterType.NONE

        margin = max(4.0 * overhead, 2.0 * gap, 600.0)  # seconds
        t_emergency = 3600.0 + margin
        t_idle_stop = 3.0 * 3600.0 + margin

        slack = time_left - remaining

        computed_phase = 1
        if time_left <= remaining + margin or slack <= t_emergency:
            computed_phase = 3
        elif slack <= t_idle_stop:
            computed_phase = 2
        else:
            computed_phase = 1

        if computed_phase > self._phase:
            self._phase = computed_phase

        if self._phase == 3:
            return ClusterType.ON_DEMAND

        if self._phase == 2:
            if not has_spot:
                return ClusterType.ON_DEMAND
            if last_cluster_type == ClusterType.ON_DEMAND and self._spot_streak < self._min_spot_confirm_steps:
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        if has_spot:
            return ClusterType.SPOT
        if slack <= margin + gap:
            return ClusterType.ON_DEMAND
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)