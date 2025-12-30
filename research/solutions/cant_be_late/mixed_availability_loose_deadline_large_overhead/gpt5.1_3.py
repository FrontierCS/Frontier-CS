import math
from typing import Any, Tuple

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        # Be robust to different Strategy.__init__ signatures.
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except TypeError:
                pass
        self._policy_initialized = False
        self._gap: float = 0.0
        self._restart_overhead: float = 0.0
        self._margin_small: float = 0.0
        self._deadline_cached: float = 0.0
        self._task_duration_cached: float = 0.0
        self._force_on_demand: bool = False
        self._unknown_task: bool = False

    def solve(self, spec_path: str) -> "Solution":
        # Optional initialization hook. We don't need spec_path here.
        return self

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

    # --- Internal helpers -------------------------------------------------

    def _initialize_policy(self) -> None:
        if self._policy_initialized:
            return
        self._policy_initialized = True

        # Cache basic configuration; be defensive about missing attributes.
        try:
            self._deadline_cached = float(getattr(self, "deadline", 0.0))
        except Exception:
            self._deadline_cached = 0.0

        try:
            self._task_duration_cached = float(getattr(self, "task_duration", 0.0))
        except Exception:
            self._task_duration_cached = 0.0

        try:
            self._gap = float(getattr(self.env, "gap_seconds", 0.0))
            if not math.isfinite(self._gap):
                self._gap = 0.0
        except Exception:
            self._gap = 0.0

        try:
            self._restart_overhead = float(getattr(self, "restart_overhead", 0.0))
            if not math.isfinite(self._restart_overhead):
                self._restart_overhead = 0.0
        except Exception:
            self._restart_overhead = 0.0

        # Detect if we lack reliable task/deadline information.
        self._unknown_task = (
            self._deadline_cached <= 0.0 or self._task_duration_cached <= 0.0
        )

        # Safety margin (seconds) we keep beyond the theoretical boundary.
        # Use a combination of gap, restart overhead, and a fixed minimum.
        self._margin_small = max(
            3.0 * self._gap,
            2.0 * self._restart_overhead,
            0.25 * 3600.0,  # 15 minutes
        )

        if self._unknown_task:
            # Without reliable task specs, fall back to always using on-demand.
            self._force_on_demand = True
            return

        # Initial slack if we committed to on-demand from time 0.
        slack = max(0.0, self._deadline_cached - self._task_duration_cached)
        # B0 is slack beyond one restart overhead and full job duration.
        B0 = slack - self._restart_overhead

        # If we don't even have a small margin of slack, we can't safely explore.
        self._force_on_demand = B0 <= self._margin_small

    def _estimate_work_done(self) -> float:
        """Estimate total completed work duration (seconds) from task_done_time."""
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return 0.0

        total_done = 0.0
        for seg in segments:
            try:
                # Numeric: treat as duration
                if isinstance(seg, (int, float)):
                    val = float(seg)
                    if math.isfinite(val) and val > 0.0:
                        total_done += val
                    continue

                # Tuple/list with (start, end)
                if isinstance(seg, (tuple, list)) and len(seg) >= 2:
                    s, e = seg[0], seg[1]
                    if isinstance(s, (int, float)) and isinstance(e, (int, float)):
                        start = float(s)
                        end = float(e)
                        if math.isfinite(start) and math.isfinite(end):
                            dur = end - start
                            if dur > 0.0:
                                total_done += dur
                            continue

                # Object with 'start'/'end' or 'start_time'/'end_time'
                for sa, ea in (("start", "end"), ("start_time", "end_time")):
                    if hasattr(seg, sa) and hasattr(seg, ea):
                        s = getattr(seg, sa)
                        e = getattr(seg, ea)
                        if isinstance(s, (int, float)) and isinstance(e, (int, float)):
                            start = float(s)
                            end = float(e)
                            if math.isfinite(start) and math.isfinite(end):
                                dur = end - start
                                if dur > 0.0:
                                    total_done += dur
                                break
            except Exception:
                # Ignore malformed segments
                continue

        # Clamp to [0, task_duration]
        td = self._task_duration_cached
        if td > 0.0:
            if total_done < 0.0:
                total_done = 0.0
            elif total_done > td:
                total_done = td
        return total_done

    def _estimate_remaining_work(self) -> float:
        """Remaining work duration (seconds)."""
        done = self._estimate_work_done()
        remaining = self._task_duration_cached - done
        if not math.isfinite(remaining):
            # Fallback: assume whole job remaining
            remaining = self._task_duration_cached
        if remaining < 0.0:
            remaining = 0.0
        return remaining

    # --- Main decision logic ----------------------------------------------

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_policy()

        # If we don't know task parameters, safest is to default to on-demand.
        if self._unknown_task:
            return ClusterType.ON_DEMAND

        # Estimate remaining work; if none, we're done.
        remaining_work = self._estimate_remaining_work()
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # If slack is too small to explore, stay on on-demand.
        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        # Get current elapsed time.
        try:
            elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
            if not math.isfinite(elapsed):
                elapsed = 0.0
        except Exception:
            # If we cannot read elapsed time, fall back to on-demand.
            return ClusterType.ON_DEMAND

        deadline = self._deadline_cached

        # If for some reason elapsed is already past deadline, use on-demand.
        if deadline > 0.0 and elapsed >= deadline:
            return ClusterType.ON_DEMAND

        # Compute slack buffer B: extra time we can "waste" (e.g., on spot/idle)
        # while still being able to switch to on-demand and finish in time.
        # B = deadline - elapsed - restart_overhead - remaining_work
        B = deadline - elapsed - self._restart_overhead - remaining_work

        # If B is small or negative, we must commit to on-demand now.
        if B <= self._gap + self._margin_small:
            return ClusterType.ON_DEMAND

        # Otherwise, we are comfortably ahead of schedule and can prioritize spot.
        if has_spot:
            return ClusterType.SPOT

        # No spot available and we still have slack: wait to avoid expensive OD.
        return ClusterType.NONE