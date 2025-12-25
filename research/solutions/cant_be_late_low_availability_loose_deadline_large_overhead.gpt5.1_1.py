from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_threshold_v1"

    def __init__(self, args):
        super().__init__(args)
        self.force_on_demand = False
        self._cached_progress = 0.0
        self._last_task_done_id = None
        self._last_task_done_len = 0
        self._segments_kind = None  # "scalar", "tuple2", "unknown"

    def solve(self, spec_path: str) -> "Solution":
        # Optional: could read spec_path if needed
        return self

    def _compute_progress(self) -> float:
        segments = getattr(self, "task_done_time", None)
        if not segments:
            # Empty or None
            self._cached_progress = 0.0
            self._last_task_done_id = id(segments)
            self._last_task_done_len = 0
            self._segments_kind = None
            return 0.0

        segs_id = id(segments)
        length = len(segments)

        # Fast path: unchanged list
        if segs_id == self._last_task_done_id and length == self._last_task_done_len:
            return self._cached_progress

        # Determine representation kind if unknown
        if self._segments_kind is None and length > 0:
            first = segments[0]
            if isinstance(first, (int, float)):
                self._segments_kind = "scalar"
            elif isinstance(first, (list, tuple)) and len(first) >= 2:
                # Try interpreting as (start, end)
                if isinstance(first[0], (int, float)) and isinstance(first[1], (int, float)):
                    self._segments_kind = "tuple2"
                else:
                    self._segments_kind = "unknown"
            else:
                self._segments_kind = "unknown"

        # If same list object and only appended new elements, update incrementally
        if segs_id == self._last_task_done_id and length > self._last_task_done_len:
            start_idx = self._last_task_done_len
            prog = self._cached_progress
        else:
            # New list or replaced; recompute from scratch
            start_idx = 0
            prog = 0.0

        kind = self._segments_kind

        if kind == "scalar":
            for v in segments[start_idx:]:
                try:
                    prog += float(v)
                except Exception:
                    continue
        elif kind == "tuple2":
            for seg in segments[start_idx:]:
                try:
                    prog += float(seg[1]) - float(seg[0])
                except Exception:
                    continue
        else:
            # Fallback: best-effort for unknown representation
            for seg in segments[start_idx:]:
                if isinstance(seg, (int, float)):
                    prog += float(seg)
                elif isinstance(seg, (list, tuple)) and len(seg) >= 2:
                    try:
                        prog += float(seg[1]) - float(seg[0])
                    except Exception:
                        continue
                else:
                    try:
                        prog += float(seg)
                    except Exception:
                        continue

        # Cache for next call
        self._cached_progress = prog
        self._last_task_done_id = segs_id
        self._last_task_done_len = length
        return prog

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Basic safety: if task already complete, do nothing
        total_required = getattr(self, "task_duration", 0.0) or 0.0
        deadline = getattr(self, "deadline", 0.0) or 0.0
        restart_overhead = getattr(self, "restart_overhead", 0.0) or 0.0

        env = self.env
        elapsed = getattr(env, "elapsed_seconds", 0.0) or 0.0
        gap = getattr(env, "gap_seconds", 1.0) or 1.0

        progress_done = self._compute_progress()
        remaining_work = max(0.0, total_required - progress_done)
        time_left = max(0.0, deadline - elapsed)

        if remaining_work <= 0.0:
            return ClusterType.NONE

        if time_left <= 0.0:
            # Already at/after deadline; run on-demand to minimize further delay
            return ClusterType.ON_DEMAND

        # Time needed if we switch to pure on-demand from now:
        # one restart overhead + remaining work
        time_needed_on_demand = remaining_work + restart_overhead

        # Guard buffer to be conservative (handles discretization, modeling mismatch)
        guard_buffer = max(2.0 * gap, 0.0)

        slack = time_left - time_needed_on_demand

        # Enter irreversible on-demand phase when slack is small
        if not self.force_on_demand and slack <= guard_buffer:
            self.force_on_demand = True

        if self.force_on_demand:
            return ClusterType.ON_DEMAND

        # Pre-commit phase: use spot whenever available, otherwise pause
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)