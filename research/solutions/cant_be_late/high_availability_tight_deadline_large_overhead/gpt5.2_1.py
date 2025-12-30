from __future__ import annotations

import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "latest_od_fallback_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self._committed_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _get_done_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0
        if isinstance(tdt, (int, float)):
            return float(tdt)

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)

        if isinstance(tdt, list):
            if not tdt:
                return 0.0

            # List of numbers: could be per-step increments or cumulative.
            if all(isinstance(x, (int, float)) for x in tdt):
                vals = [float(x) for x in tdt]
                if len(vals) >= 2 and all(vals[i] <= vals[i + 1] + 1e-9 for i in range(len(vals) - 1)):
                    last = vals[-1]
                    # Heuristic: monotone list with last close to duration => cumulative.
                    if task_duration > 0 and last <= task_duration * 1.25:
                        return max(0.0, last)
                return max(0.0, sum(vals))

            # List of (start, end) segments.
            if all(isinstance(x, (tuple, list)) and len(x) >= 2 for x in tdt):
                total = 0.0
                for seg in tdt:
                    a, b = seg[0], seg[1]
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        total += max(0.0, float(b) - float(a))
                    elif isinstance(a, (int, float)) and not isinstance(b, (int, float)):
                        total += max(0.0, float(a))
                return max(0.0, total)

            # Fallback: try last numeric element.
            for x in reversed(tdt):
                if isinstance(x, (int, float)):
                    return max(0.0, float(x))

        return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)

        done = self._get_done_seconds()
        remaining_work = max(0.0, task_duration - done)

        if remaining_work <= 1e-6:
            return ClusterType.NONE

        remaining_time = max(0.0, deadline - elapsed)

        # If we must start/continue on-demand to guarantee completion (worst-case: no spot ever again).
        overhead_if_start_od = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead

        # Safety buffer for timestep discretization and potential immediate unavailability.
        safety = restart_overhead + max(2.0 * gap, 0.0)

        must_use_od = remaining_time <= (remaining_work + overhead_if_start_od + safety)

        if self._committed_to_od or must_use_od:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)