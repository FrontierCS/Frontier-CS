from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_threshold_v1"

    def solve(self, spec_path: str) -> "Solution":
        # Optional: store spec path; thresholds are computed lazily in _step.
        self.spec_path = spec_path
        self._initialized = False
        self._work_done_cache = 0.0
        self._last_segment_len = -1
        self.force_od = False
        return self

    def _initialize_if_needed(self):
        if getattr(self, "_initialized", False):
            return

        self._initialized = True

        # Compute total slack = deadline - required compute time.
        try:
            total_slack = float(self.deadline) - float(self.task_duration)
        except Exception:
            total_slack = 0.0
        if total_slack < 0.0:
            total_slack = 0.0
        self.total_slack = total_slack

        # Environment parameters.
        gap = 0.0
        if hasattr(self, "env") and hasattr(self.env, "gap_seconds"):
            try:
                gap = float(self.env.gap_seconds)
            except Exception:
                gap = 0.0

        overhead = 0.0
        if hasattr(self, "restart_overhead"):
            try:
                overhead = float(self.restart_overhead)
            except Exception:
                overhead = 0.0

        # Thresholds as fractions of total slack (tuned for this problem scale).
        wait_ratio = 0.4   # start using OD on spot outages once slack < 40% of total.
        commit_ratio = 0.08  # permanently switch to OD once slack < 8% of total.

        wait_slack = total_slack * wait_ratio
        commit_slack = total_slack * commit_ratio

        # Ensure a minimum cushion around a few restart overheads and time steps.
        min_commit = 3.0 * (overhead + gap)
        if commit_slack < min_commit:
            commit_slack = min_commit

        # Wait threshold should be at least 2x commit and not exceed total slack.
        if wait_slack < 2.0 * commit_slack:
            wait_slack = 2.0 * commit_slack
        if wait_slack > total_slack:
            wait_slack = total_slack

        self.wait_slack_threshold = wait_slack
        self.commit_slack_threshold = commit_slack

        self._work_done_cache = 0.0
        self._last_segment_len = -1
        self.force_od = False

    def _segment_duration(self, seg) -> float:
        """Best-effort extraction of a segment's duration in seconds."""
        if seg is None:
            return 0.0

        # Numeric: treat as duration.
        if isinstance(seg, (int, float)):
            return float(seg)

        # List/tuple: [start, end] or [start, duration].
        if isinstance(seg, (list, tuple)):
            if len(seg) >= 2:
                a = seg[0]
                b = seg[1]
                try:
                    a_f = float(a)
                    b_f = float(b)
                    # If b >= a, interpret as end - start; else as duration.
                    if b_f >= a_f:
                        return b_f - a_f
                    else:
                        return b_f
                except Exception:
                    pass

        # Dict-based representations.
        if isinstance(seg, dict):
            if "duration" in seg:
                try:
                    return float(seg["duration"])
                except Exception:
                    pass
            if "start" in seg and "end" in seg:
                try:
                    return float(seg["end"]) - float(seg["start"])
                except Exception:
                    pass

        # Generic object with attributes.
        for attr in ("duration", "len", "length"):
            if hasattr(seg, attr):
                try:
                    return float(getattr(seg, attr))
                except Exception:
                    pass

        if hasattr(seg, "start") and hasattr(seg, "end"):
            try:
                return float(getattr(seg, "end")) - float(getattr(seg, "start"))
            except Exception:
                pass

        # Fallback if format is unknown.
        return 0.0

    def _compute_work_done(self) -> float:
        """Compute total task progress using cached segments when possible."""
        segs = getattr(self, "task_done_time", None)
        if not segs:
            self._work_done_cache = 0.0
            self._last_segment_len = 0
            return 0.0

        try:
            n = len(segs)
        except TypeError:
            # Not sized; compute afresh.
            total = 0.0
            for seg in segs:
                total += self._segment_duration(seg)
            self._work_done_cache = total
            self._last_segment_len = -1
            return total

        if n == self._last_segment_len:
            return self._work_done_cache

        total = 0.0
        for seg in segs:
            total += self._segment_duration(seg)

        self._work_done_cache = total
        self._last_segment_len = n
        return total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_if_needed()

        # If we've committed to on-demand only, stay there to avoid extra restarts.
        if getattr(self, "force_od", False):
            return ClusterType.ON_DEMAND

        work_done = self._compute_work_done()
        try:
            total_duration = float(self.task_duration)
        except Exception:
            total_duration = 0.0

        remaining_work = total_duration - work_done
        if remaining_work <= 0.0:
            # Task is effectively complete.
            return ClusterType.NONE

        # Deadline and time left.
        if hasattr(self, "deadline"):
            try:
                deadline = float(self.deadline)
            except Exception:
                deadline = None
        else:
            deadline = None

        if deadline is None:
            # No deadline info; fall back to simple spot-preferred behavior.
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        current_time = 0.0
        if hasattr(self, "env") and hasattr(self.env, "elapsed_seconds"):
            try:
                current_time = float(self.env.elapsed_seconds)
            except Exception:
                current_time = 0.0

        time_left = deadline - current_time

        # If we're already past the deadline, best-effort with on-demand.
        if time_left <= 0.0:
            self.force_od = True
            return ClusterType.ON_DEMAND

        slack = time_left - remaining_work

        commit_threshold = getattr(self, "commit_slack_threshold", 0.0)
        wait_threshold = getattr(self, "wait_slack_threshold", commit_threshold * 2.0)

        # If at or below our commit threshold, permanently switch to on-demand.
        if slack <= commit_threshold or slack <= 0.0:
            self.force_od = True
            return ClusterType.ON_DEMAND

        # High-slack region: prioritize cost savings; wait for spot when unavailable.
        if slack > wait_threshold:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE

        # Medium-slack region: use spot when available, OD when not.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)