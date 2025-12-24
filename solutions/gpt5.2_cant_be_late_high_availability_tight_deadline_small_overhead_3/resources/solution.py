import argparse
from typing import Any, Optional

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:  # pragma: no cover
    from enum import Enum

    class ClusterType(Enum):
        SPOT = "spot"
        ON_DEMAND = "on_demand"
        NONE = "none"

    class Strategy:
        def __init__(self, *args, **kwargs):
            self.env = type("Env", (), {"elapsed_seconds": 0, "gap_seconds": 60, "cluster_type": ClusterType.NONE})()
            self.task_duration = 0
            self.task_done_time = []
            self.deadline = 0
            self.restart_overhead = 0


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except TypeError:
                pass
        self.args = args
        self._inited = False
        self._entered_od_mode = False
        self._total_slack = 0.0
        self._risk_buffer = 0.0
        self._spot_seen = 0
        self._spot_avail = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _safe_float(x: Any, default: float = 0.0) -> float:
        try:
            return float(x)
        except Exception:
            return default

    def _work_done_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if not td:
            return 0.0
        total = 0.0
        try:
            for seg in td:
                if seg is None:
                    continue
                if isinstance(seg, (int, float)):
                    total += float(seg)
                elif isinstance(seg, (tuple, list)) and len(seg) >= 2:
                    a = self._safe_float(seg[0], 0.0)
                    b = self._safe_float(seg[1], 0.0)
                    if b >= a:
                        total += (b - a)
                elif isinstance(seg, dict):
                    a = self._safe_float(seg.get("start", seg.get("begin", 0.0)), 0.0)
                    b = self._safe_float(seg.get("end", seg.get("finish", 0.0)), 0.0)
                    if b >= a:
                        total += (b - a)
        except Exception:
            pass
        return max(0.0, total)

    def _lazy_init(self) -> None:
        if self._inited:
            return
        self._inited = True
        self._entered_od_mode = False
        self._spot_seen = 0
        self._spot_avail = 0

        task_duration = self._safe_float(getattr(self, "task_duration", 0.0), 0.0)
        deadline = self._safe_float(getattr(self, "deadline", 0.0), 0.0)
        self._total_slack = max(0.0, deadline - task_duration)

        ro = self._safe_float(getattr(self, "restart_overhead", 0.0), 0.0)
        self._risk_buffer = max(2.0 * ro, 0.25 * 3600.0)  # at least 15 minutes safety

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        self._spot_seen += 1
        if has_spot:
            self._spot_avail += 1

        elapsed = self._safe_float(getattr(self.env, "elapsed_seconds", 0.0), 0.0)
        task_duration = self._safe_float(getattr(self, "task_duration", 0.0), 0.0)
        deadline = self._safe_float(getattr(self, "deadline", 0.0), 0.0)

        work_done = self._work_done_seconds()
        remaining_work = max(0.0, task_duration - work_done)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        remaining_time = max(0.0, deadline - elapsed)
        slack_remaining = remaining_time - remaining_work

        if self._entered_od_mode:
            return ClusterType.ON_DEMAND

        if slack_remaining <= self._risk_buffer:
            self._entered_od_mode = True
            return ClusterType.ON_DEMAND

        idle_used = max(0.0, elapsed - work_done)

        avail_rate = (self._spot_avail / self._spot_seen) if self._spot_seen > 0 else 0.7
        wait_frac = 0.2 + 0.8 * max(0.0, min(1.0, avail_rate))
        wait_frac = max(0.25, min(0.9, wait_frac))
        wait_budget = self._total_slack * wait_frac

        if has_spot:
            return ClusterType.SPOT

        if idle_used < wait_budget and slack_remaining > (self._risk_buffer + self._safe_float(getattr(self, "restart_overhead", 0.0), 0.0)):
            return ClusterType.NONE

        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
