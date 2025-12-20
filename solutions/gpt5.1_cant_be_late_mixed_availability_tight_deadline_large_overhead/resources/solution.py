from typing import Any, Tuple, List
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v1"

    def __init__(self, args=None):
        super().__init__(args)
        # Internal state
        self._committed_to_od = False
        self._cached_work_done = 0.0
        self._last_segments_len = 0
        self._commit_slack_threshold = None

    def solve(self, spec_path: str) -> "Solution":
        # Optional initialization hook; we don't need spec_path for now.
        return self

    # --- Internal helpers -------------------------------------------------

    def _segment_to_duration(self, seg: Any) -> float:
        """Best-effort conversion of a 'segment' entry to a duration in seconds."""
        if seg is None:
            return 0.0

        # Plain numeric: assume already a duration
        if isinstance(seg, (int, float)):
            try:
                return float(seg)
            except (TypeError, ValueError):
                return 0.0

        # Tuple or list; assume (start, end)
        if isinstance(seg, (tuple, list)) and len(seg) >= 2:
            start, end = seg[0], seg[1]
            try:
                return float(end) - float(start)
            except (TypeError, ValueError):
                pass

        # Generic object: try common attribute patterns
        # 1) duration attribute
        d = getattr(seg, "duration", None)
        if d is not None:
            try:
                return float(d)
            except (TypeError, ValueError):
                pass

        # 2) (start, end) style attributes with common names
        for s_name, e_name in [
            ("start", "end"),
            ("start_time", "end_time"),
            ("start_ts", "end_ts"),
        ]:
            s = getattr(seg, s_name, None)
            e = getattr(seg, e_name, None)
            if s is not None and e is not None:
                try:
                    return float(e) - float(s)
                except (TypeError, ValueError):
                    continue

        # Fallback: can't interpret; be conservative (0 progress)
        return 0.0

    def _update_work_done(self) -> float:
        """Incrementally update and return total work done (seconds)."""
        segments = getattr(self, "task_done_time", None)
        if not segments:
            # No segments yet
            self._cached_work_done = 0.0
            self._last_segments_len = 0
            return 0.0

        # If list shrank or was replaced, reset cache conservatively.
        try:
            current_len = len(segments)
        except TypeError:
            # Not a list-like; can't reason safely, so reset and try naive summation.
            self._cached_work_done = 0.0
            self._last_segments_len = 0
            try:
                total = 0.0
                for seg in segments:
                    total += self._segment_to_duration(seg)
                self._cached_work_done = total
                self._last_segments_len = len(segments)
                return total
            except Exception:
                # Very defensive: if even this fails, treat as 0 progress
                return 0.0

        if current_len < self._last_segments_len:
            # List got reset/overwritten; recompute from scratch
            total = 0.0
            for seg in segments:
                total += self._segment_to_duration(seg)
            self._cached_work_done = total
            self._last_segments_len = current_len
            return total

        # Process only new segments
        if current_len > self._last_segments_len:
            for i in range(self._last_segments_len, current_len):
                self._cached_work_done += self._segment_to_duration(segments[i])
            self._last_segments_len = current_len

        return self._cached_work_done

    def _ensure_commit_threshold(self):
        """Initialize the commit slack threshold if not yet set."""
        if self._commit_slack_threshold is not None:
            return

        # Total available slack if we ran on-demand from start.
        try:
            total_slack = max(float(self.deadline) - float(self.task_duration), 0.0)
        except Exception:
            total_slack = 0.0

        try:
            gap = float(getattr(self.env, "gap_seconds", 60.0))
        except Exception:
            gap = 60.0

        try:
            overhead = float(getattr(self, "restart_overhead", 0.0))
        except Exception:
            overhead = 0.0

        # Base threshold: enough to cover a couple of overheads + a few steps of granularity.
        base_threshold = 2.0 * overhead + 4.0 * gap

        # Also require we keep at least ~20% of global slack in reserve (if any).
        relative_threshold = 0.2 * total_slack

        self._commit_slack_threshold = max(base_threshold, relative_threshold, 0.0)

        # If total slack is smaller than this threshold, it's still okay:
        # we will simply commit immediately (no reliance on spot).

    # --- Core decision logic ----------------------------------------------

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize commit threshold using environment parameters.
        self._ensure_commit_threshold()

        # Update our estimate of work done so far.
        work_done = self._update_work_done()

        # Defensive bounds
        try:
            task_duration = float(self.task_duration)
        except Exception:
            task_duration = work_done  # fallback

        try:
            elapsed = float(self.env.elapsed_seconds)
        except Exception:
            elapsed = work_done

        try:
            deadline = float(self.deadline)
        except Exception:
            # If deadline unknown, behave conservatively: always on-demand.
            return ClusterType.ON_DEMAND

        remaining_work = max(task_duration - work_done, 0.0)
        time_left = max(deadline - elapsed, 0.0)

        # Slack left relative to "always-on on-demand" baseline.
        slack_left = time_left - remaining_work

        # If slack_left is negative, it's already impossible to meet deadline
        # with perfect on-demand from now. We still do our best: commit to OD.
        if not self._committed_to_od:
            if slack_left <= self._commit_slack_threshold:
                self._committed_to_od = True

        # Once committed, always choose on-demand to guarantee no further risk.
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        gap = float(getattr(self.env, "gap_seconds", 60.0))

        # Not yet committed: use spot aggressively but manage slack.
        if has_spot:
            # Spot is available and we still have enough slack buffer.
            return ClusterType.SPOT

        # No spot available, not yet committed.
        # Decide whether we can afford to wait one gap interval.
        # If waiting would still leave us above the commit threshold, we wait.
        if slack_left - gap > self._commit_slack_threshold:
            return ClusterType.NONE

        # Can't afford to wait longer: commit to on-demand from this point.
        self._committed_to_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
