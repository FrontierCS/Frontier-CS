import json
import os
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Any):
        super().__init__(args)
        self._committed_od = False
        self._seen_steps = 0
        self._spot_steps = 0
        self._spot_ema = 0.65
        self._ema_alpha = 0.06
        self._base_safety_seconds = 2.0 * 3600.0
        self._max_safety_seconds = 4.0 * 3600.0
        self._min_safety_seconds = 0.5 * 3600.0
        self._spec_overrides_applied = False

    def solve(self, spec_path: str) -> "Solution":
        if spec_path and os.path.exists(spec_path):
            cfg = None
            try:
                with open(spec_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                cfg = None
            if cfg is None:
                try:
                    import yaml  # type: ignore

                    with open(spec_path, "r", encoding="utf-8") as f:
                        cfg = yaml.safe_load(f)
                except Exception:
                    cfg = None

            if isinstance(cfg, dict):
                safety_hours = cfg.get("safety_margin_hours", None)
                if isinstance(safety_hours, (int, float)) and safety_hours > 0:
                    self._base_safety_seconds = float(safety_hours) * 3600.0

                ema_alpha = cfg.get("spot_ema_alpha", None)
                if isinstance(ema_alpha, (int, float)) and 0 < float(ema_alpha) <= 1:
                    self._ema_alpha = float(ema_alpha)

                min_safety_hours = cfg.get("min_safety_hours", None)
                if isinstance(min_safety_hours, (int, float)) and float(min_safety_hours) >= 0:
                    self._min_safety_seconds = float(min_safety_hours) * 3600.0

                max_safety_hours = cfg.get("max_safety_hours", None)
                if isinstance(max_safety_hours, (int, float)) and float(max_safety_hours) > 0:
                    self._max_safety_seconds = float(max_safety_hours) * 3600.0

        self._spec_overrides_applied = True
        return self

    def _work_done_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0
        if isinstance(tdt, (int, float)):
            return float(tdt)
        if isinstance(tdt, (list, tuple)):
            total = 0.0
            for x in tdt:
                if isinstance(x, (int, float)):
                    total += float(x)
                elif isinstance(x, (list, tuple)) and x:
                    v = x[-1]
                    if isinstance(v, (int, float)):
                        total += float(v)
            return total
        return 0.0

    def _safety_seconds(self, remaining_work: float, gap_seconds: float, restart_overhead: float) -> float:
        p = max(0.05, min(0.95, float(self._spot_ema)))
        if p >= 0.75:
            base = min(self._base_safety_seconds, 1.25 * 3600.0)
        elif p >= 0.60:
            base = min(self._base_safety_seconds, 1.75 * 3600.0)
        else:
            base = max(self._base_safety_seconds, 2.25 * 3600.0)

        extra = 0.02 * remaining_work
        extra = min(extra, 1.25 * 3600.0)

        overhead_buffer = max(0.0, 10.0 * float(restart_overhead))
        step_buffer = 2.0 * float(gap_seconds)

        safety = base + extra + overhead_buffer + step_buffer
        safety = max(self._min_safety_seconds, min(self._max_safety_seconds, safety))
        return safety

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._seen_steps += 1
        if has_spot:
            self._spot_steps += 1
        x = 1.0 if has_spot else 0.0
        self._spot_ema = (1.0 - self._ema_alpha) * self._spot_ema + self._ema_alpha * x

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 0.0))
        deadline = float(getattr(self, "deadline", 0.0))
        task_duration = float(getattr(self, "task_duration", 0.0))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))

        work_done = self._work_done_seconds()
        remaining_work = max(0.0, task_duration - work_done)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        remaining_time = deadline - elapsed
        if remaining_time <= 0.0:
            return ClusterType.NONE

        safety = self._safety_seconds(remaining_work=remaining_work, gap_seconds=gap, restart_overhead=restart_overhead)
        slack = remaining_time - remaining_work

        if self._committed_od or slack <= safety or remaining_time <= remaining_work + (2.0 * gap):
            self._committed_od = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
