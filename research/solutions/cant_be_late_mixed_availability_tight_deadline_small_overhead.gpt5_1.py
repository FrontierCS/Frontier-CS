from typing import Any, Iterable
import math

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_robust_v1"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except Exception:
            pass
        self.args = args
        self._locked_on_demand = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _compute_progress_seconds(self) -> float:
        # Robustly infer progress from task_done_time in various possible forms
        ts = getattr(self, "task_done_time", None)
        if ts is None:
            return 0.0

        # Ensure iterable materialization if needed
        if not isinstance(ts, list) and isinstance(ts, Iterable):
            ts = list(ts)

        if not ts:
            return 0.0

        gap = getattr(self.env, "gap_seconds", 60.0) or 60.0

        first = ts[0]
        progress = 0.0

        # Case 1: list of tuple/list segments: [(start, end), ...]
        if isinstance(first, (tuple, list)) and len(first) >= 2 and all(
            isinstance(x, (int, float)) for x in first[:2]
        ):
            total = 0.0
            for seg in ts:
                try:
                    a, b = seg[0], seg[1]
                    total += max(0.0, float(b) - float(a))
                except Exception:
                    # Fallback to counting if unexpected shape
                    total = None
                    break
            if total is not None:
                progress = total
            else:
                progress = len(ts) * gap

        # Case 2: objects with .start and .end
        elif hasattr(first, "start") and hasattr(first, "end"):
            total = 0.0
            for seg in ts:
                try:
                    total += max(0.0, float(seg.end) - float(seg.start))
                except Exception:
                    total = None
                    break
            if total is not None:
                progress = total
            else:
                progress = len(ts) * gap

        # Case 3: objects with .duration
        elif hasattr(first, "duration"):
            total = 0.0
            for seg in ts:
                try:
                    total += float(getattr(seg, "duration"))
                except Exception:
                    total = None
                    break
            if total is not None:
                progress = total
            else:
                progress = len(ts) * gap

        # Case 4: list of numbers (ambiguous). Assume 1 entry per progress step.
        elif isinstance(first, (int, float)):
            progress = len(ts) * gap

        else:
            progress = len(ts) * gap

        # Clamp to task duration
        td = getattr(self, "task_duration", None)
        if isinstance(td, (int, float)) and td is not None:
            return min(float(td), float(progress))
        return float(progress)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Quick guards for required attributes
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", elapsed + 1e9) or (elapsed + 1e9))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)

        # Compute remaining work
        progress = self._compute_progress_seconds()
        remaining = max(0.0, task_duration - progress)

        # If job is done: stop
        if remaining <= 0.0:
            self._locked_on_demand = False
            return ClusterType.NONE

        # Time left until deadline
        time_left = max(0.0, deadline - elapsed)

        # If we're already out of time, try to use OD
        if time_left <= 0.0:
            self._locked_on_demand = True
            return ClusterType.ON_DEMAND

        # Safety buffer to account for discretization and overhead uncertainties
        safe_buffer = max(gap, restart_overhead)

        # Commit to on-demand if we no longer have enough time to wait
        # i.e., if we need at least remaining + restart_overhead seconds from now.
        if time_left <= remaining + restart_overhead:
            self._locked_on_demand = True

        # If locked in on-demand mode, always choose on-demand until finish
        if self._locked_on_demand:
            return ClusterType.ON_DEMAND

        # If currently on on-demand and close to the threshold, keep it to avoid risk
        if last_cluster_type == ClusterType.ON_DEMAND:
            if time_left <= remaining + restart_overhead + safe_buffer:
                return ClusterType.ON_DEMAND

        # Compute slack that can be spent idling or on opportunistic spot with no guarantee of progress
        idle_budget = time_left - (remaining + restart_overhead)

        # Decision logic:
        # - If we have comfortable slack, use SPOT if available; otherwise idle.
        # - If slack is tight, switch/run on ON_DEMAND.
        if idle_budget > safe_buffer:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE
        else:
            # If we're currently on OD and slack is only mildly tight but has_spot is available,
            # the guard above already kept OD; otherwise, choose OD to ensure deadline.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)