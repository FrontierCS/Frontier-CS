from typing import Any, List, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cantb_late_commit_wait"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

    _from_args = classmethod(_from_args)

    def _sum_work_done_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0
        # If already a numeric value
        if isinstance(td, (int, float)):
            return float(td)
        # If empty-like
        try:
            if not td:
                return 0.0
        except Exception:
            try:
                return float(td)
            except Exception:
                return 0.0
        # Now handle list-like
        try:
            first = td[0]
        except Exception:
            # Fallback: try summing
            total = 0.0
            try:
                for v in td:
                    total += float(v)
            except Exception:
                total = 0.0
            return total

        # Case: list of (start, end) tuples/lists
        if isinstance(first, (list, tuple)) and len(first) >= 2:
            total = 0.0
            for seg in td:
                try:
                    s = float(seg[0])
                    e = float(seg[1])
                    if e > s:
                        total += e - s
                except Exception:
                    continue
            return total
        # Case: list of numeric durations
        total = 0.0
        for v in td:
            try:
                total += float(v)
            except Exception:
                continue
        return total

    def _reset_run_state_if_needed(self):
        if not hasattr(self, "_sticky_od"):
            self._sticky_od = False
        elapsed = getattr(self.env, "elapsed_seconds", None)
        if not hasattr(self, "_last_seen_elapsed"):
            self._last_seen_elapsed = elapsed
            if elapsed == 0:
                self._sticky_od = False
            return
        # Detect new run by elapsed time reset/decrease
        if elapsed is not None and self._last_seen_elapsed is not None:
            if elapsed < self._last_seen_elapsed:
                self._sticky_od = False
        self._last_seen_elapsed = elapsed

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._reset_run_state_if_needed()

        # If we've previously committed to OD or currently on OD, stay on OD.
        if getattr(self, "_sticky_od", False) or last_cluster_type == ClusterType.ON_DEMAND:
            self._sticky_od = True
            return ClusterType.ON_DEMAND

        elapsed = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
        time_left = (self.deadline or 0.0) - elapsed

        # Compute remaining work
        done = self._sum_work_done_seconds()
        remaining = max((self.task_duration or 0.0) - done, 0.0)

        # If finished, do nothing
        if remaining <= 0.0:
            return ClusterType.NONE

        # Commitment logic
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        # Safety margin to handle step discretization and decision latency
        safety_margin = max(gap, 0.0)

        # Slack = extra time beyond what's needed to compute remaining work
        slack = time_left - remaining

        # If slack is too small to afford another restart overhead (plus margin), commit to OD
        if slack <= (overhead + safety_margin):
            self._sticky_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, prefer spot when available; if not available, wait (NONE)
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable but we still have enough time buffer: wait
        return ClusterType.NONE