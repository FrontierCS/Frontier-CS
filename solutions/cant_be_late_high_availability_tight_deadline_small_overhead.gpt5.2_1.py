from __future__ import annotations

import json
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "reserve_wait_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._initialized = False
        self._spec: dict[str, Any] = {}
        self._spot_streak = 0
        self._committed_od = False

        # Conservative defaults (seconds)
        self._min_reserve_seconds = 30 * 60  # keep at least 30 minutes of slack
        self._min_commit_buffer_seconds = 60  # small buffer against edge rounding
        self._switch_to_spot_streak = 2  # require 2 consecutive "spot available" steps before switching from OD->Spot

    def solve(self, spec_path: str) -> "Solution":
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                self._spec = json.load(f) if spec_path else {}
        except Exception:
            self._spec = {}

        # Allow optional config overrides
        try:
            cfg = self._spec.get("strategy_config", self._spec) if isinstance(self._spec, dict) else {}
            if isinstance(cfg, dict):
                if "min_reserve_seconds" in cfg:
                    self._min_reserve_seconds = float(cfg["min_reserve_seconds"])
                if "switch_to_spot_streak" in cfg:
                    self._switch_to_spot_streak = int(cfg["switch_to_spot_streak"])
                if "min_commit_buffer_seconds" in cfg:
                    self._min_commit_buffer_seconds = float(cfg["min_commit_buffer_seconds"])
        except Exception:
            pass

        return self

    @staticmethod
    def _sum_done_seconds(task_done_time: Any) -> float:
        if not task_done_time:
            return 0.0
        total = 0.0
        try:
            for x in task_done_time:
                if x is None:
                    continue
                if isinstance(x, (int, float)):
                    total += float(x)
                    continue
                if isinstance(x, dict):
                    # Common patterns: {"start":..., "end":...} or {"duration":...}
                    if "duration" in x and isinstance(x["duration"], (int, float)):
                        total += float(x["duration"])
                    elif "start" in x and "end" in x and isinstance(x["start"], (int, float)) and isinstance(
                        x["end"], (int, float)
                    ):
                        total += max(0.0, float(x["end"]) - float(x["start"]))
                    continue
                if isinstance(x, (list, tuple)) and len(x) >= 2:
                    a, b = x[0], x[1]
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        # Interpret as [start, end]
                        total += max(0.0, float(b) - float(a))
                        continue
        except Exception:
            pass
        return float(total)

    def _ensure_init(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._spot_streak = 0
        self._committed_od = False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()

        if has_spot:
            self._spot_streak += 1
        else:
            self._spot_streak = 0

        try:
            elapsed = float(self.env.elapsed_seconds)
        except Exception:
            elapsed = 0.0
        try:
            gap = float(self.env.gap_seconds)
        except Exception:
            gap = 0.0

        restart_overhead = float(getattr(self, "restart_overhead", 0.0))
        deadline = float(getattr(self, "deadline", 0.0))
        task_duration = float(getattr(self, "task_duration", 0.0))

        done = self._sum_done_seconds(getattr(self, "task_done_time", None))
        remaining_work = max(0.0, task_duration - done)
        time_left = max(0.0, deadline - elapsed)

        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Slack: how much non-progress time we can still afford.
        slack = time_left - remaining_work

        # Critical buffer to ensure we can always start OD (including one reaction step and overhead).
        critical = restart_overhead + 2.0 * gap + self._min_commit_buffer_seconds

        # Reserve slack we will not spend waiting, to avoid deadline risk.
        reserve = max(self._min_reserve_seconds, critical)

        # If we're very close, commit to OD and never leave it.
        if slack <= critical or time_left <= 0.0:
            self._committed_od = True

        if self._committed_od:
            return ClusterType.ON_DEMAND

        if has_spot:
            # Prefer spot whenever available, but avoid flapping OD->SPOT when slack is too tight.
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT

            # If we were on OD, only switch to spot if:
            # - spot appears stable for a couple steps
            # - we still have enough slack to tolerate a future interruption + restart
            if last_cluster_type == ClusterType.ON_DEMAND:
                if self._spot_streak >= self._switch_to_spot_streak and slack > (reserve + restart_overhead + gap):
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND

            # From NONE (or other), use spot immediately.
            return ClusterType.SPOT

        # No spot available: wait if slack permits, otherwise run on-demand.
        if slack > (reserve + gap):
            return ClusterType.NONE
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
