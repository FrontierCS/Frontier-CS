import math
from typing import Any, List, Tuple

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v1"

    def solve(self, spec_path: str) -> "Solution":
        # Initialize internal state
        self.committed_to_od = False
        self._last_task_done_len = 0
        self._cached_work_done = 0.0
        self._segments_are_pairs = None
        return self

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

    def _update_work_done_cache(self) -> None:
        """Incrementally update cached work-done estimate from self.task_done_time."""
        segments = getattr(self, "task_done_time", None)

        if segments is None:
            return

        # If it's not a list/tuple, try to interpret directly as a scalar amount
        if not isinstance(segments, (list, tuple)):
            try:
                val = float(segments)
            except Exception:
                return
            self._cached_work_done = max(val, 0.0)
            self._last_task_done_len = 1
            return

        n = len(segments)

        # Handle potential reset of the list
        if n < getattr(self, "_last_task_done_len", 0):
            # List shrunk or reset; recompute from scratch
            self._cached_work_done = 0.0
            self._last_task_done_len = 0
            self._segments_are_pairs = None

        # Detect structure (pair vs scalar) if unknown
        if self._segments_are_pairs is None:
            for i in range(self._last_task_done_len, n):
                seg = segments[i]
                if isinstance(seg, (list, tuple)) and len(seg) >= 2:
                    self._segments_are_pairs = True
                    break
                else:
                    try:
                        float(seg)
                        self._segments_are_pairs = False
                        break
                    except Exception:
                        continue
            # If still None, nothing useful to add yet
            if self._segments_are_pairs is None:
                self._last_task_done_len = n
                return

        # Accumulate new segments
        for i in range(self._last_task_done_len, n):
            seg = segments[i]
            try:
                if self._segments_are_pairs and isinstance(seg, (list, tuple)) and len(seg) >= 2:
                    delta = float(seg[1]) - float(seg[0])
                else:
                    delta = float(seg)
                if delta > 0:
                    self._cached_work_done += delta
            except Exception:
                continue

        self._last_task_done_len = n

        # Clamp to non-negative
        if self._cached_work_done < 0:
            self._cached_work_done = 0.0

    def _estimate_work_done(self) -> float:
        """Return conservative estimate of work done (seconds)."""
        if not hasattr(self, "_last_task_done_len"):
            self._last_task_done_len = 0
            self._cached_work_done = 0.0
            self._segments_are_pairs = None

        self._update_work_done_cache()
        # Do not exceed total task_duration
        total = getattr(self, "task_duration", None)
        if total is None:
            return self._cached_work_done
        return max(0.0, min(self._cached_work_done, float(total)))

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Ensure state initialized even if solve() wasn't called
        if not hasattr(self, "committed_to_od"):
            self.committed_to_od = False
        if not hasattr(self, "_last_task_done_len"):
            self._last_task_done_len = 0
            self._cached_work_done = 0.0
            self._segments_are_pairs = None

        # Estimate remaining work and time
        work_done = self._estimate_work_done()
        task_duration = float(getattr(self, "task_duration", 0.0))
        remaining_work = max(task_duration - work_done, 0.0)

        # If task already done, no need to run anything
        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        deadline = float(getattr(self, "deadline", 0.0))
        remaining_time = max(deadline - elapsed, 0.0)

        # If no time left, nothing sensible to do
        if remaining_time <= 0.0:
            # Returning NONE avoids extra cost; failure (if any) is already determined
            return ClusterType.NONE

        # Compute slack (future idle/overhead budget)
        slack = remaining_time - remaining_work

        # Parameters for safety margin
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        # Base buffer: 30 minutes, but also scale with gap and overhead
        base_buffer_seconds = 1800.0  # 0.5 hours
        commit_buffer = max(base_buffer_seconds, 10.0 * gap, 6.0 * overhead)

        # We want at least (overhead + commit_buffer) slack when still gambling on spot
        needed_margin = overhead + commit_buffer

        # If we're already in tight regime, permanently commit to on-demand
        if slack <= needed_margin or remaining_time <= (remaining_work + overhead):
            self.committed_to_od = True

        if self.committed_to_od:
            # In committed regime, avoid any further preemptions by always using on-demand
            return ClusterType.ON_DEMAND

        # Cheap regime: use spot whenever available, otherwise wait
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE