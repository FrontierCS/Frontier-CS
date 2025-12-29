from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self._policy_initialized = False
        self._total_done = 0.0
        self._last_task_done_len = 0
        self._segments_id = None
        self.initial_slack = 0.0
        self.commit_threshold = 0.0
        self.wait_threshold = 0.0
        self.gap_seconds = 0.0
        self._final_od_commit = False

    def solve(self, spec_path: str) -> "Solution":
        # Optional pre-processing; not used in this heuristic.
        return self

    def _init_policy(self):
        # Initialize thresholds based on environment and task parameters.
        try:
            self.gap_seconds = float(getattr(self.env, "gap_seconds", 1.0))
        except Exception:
            self.gap_seconds = 1.0

        try:
            task_duration = float(self.task_duration)
        except Exception:
            task_duration = 0.0

        try:
            deadline = float(self.deadline)
        except Exception:
            deadline = task_duration

        try:
            overhead = float(self.restart_overhead)
        except Exception:
            overhead = 0.0
            self.restart_overhead = overhead

        self.initial_slack = max(0.0, deadline - task_duration)

        # We must not risk missing deadline: require at least one gap of slack
        # (plus restart_overhead which is included in F) before we consider spot/none.
        self.commit_threshold = max(self.gap_seconds, 0.0)

        # Allow waiting (NONE) only when we have comfortable slack.
        # Use 50% of initial slack as high-slack region; ensure >= commit_threshold.
        if self.initial_slack > 0.0:
            base_wait = 0.5 * self.initial_slack
        else:
            base_wait = 0.0
        self.wait_threshold = max(base_wait, self.commit_threshold)

        self._policy_initialized = True

    def _segment_duration(self, seg) -> float:
        # Robustly compute duration from a segment representation.
        try:
            if isinstance(seg, (list, tuple)):
                if len(seg) >= 2:
                    # Assume (start, end) or (start, duration)
                    start = seg[0]
                    end = seg[1]
                    return max(0.0, float(end) - float(start))
                elif len(seg) == 1:
                    return max(0.0, float(seg[0]))
                else:
                    return 0.0
            else:
                return max(0.0, float(seg))
        except Exception:
            return 0.0

    def _update_progress(self):
        # Update self._total_done from self.task_done_time.
        segments = getattr(self, "task_done_time", None)
        if segments is None:
            return

        # If it's not a sequence, treat it as scalar total.
        try:
            n = len(segments)
        except TypeError:
            try:
                self._total_done = max(0.0, float(segments))
            except Exception:
                self._total_done = 0.0
            self._last_task_done_len = 0
            self._segments_id = None
            return

        # If the underlying object changed or shrank, recompute from scratch.
        if (
            self._segments_id is None
            or id(segments) != self._segments_id
            or n < self._last_task_done_len
        ):
            self._segments_id = id(segments)
            self._last_task_done_len = n
            total = 0.0
            for seg in segments:
                total += self._segment_duration(seg)
            self._total_done = total
        elif n > self._last_task_done_len:
            # Incremental update for appended segments.
            for idx in range(self._last_task_done_len, n):
                self._total_done += self._segment_duration(segments[idx])
            self._last_task_done_len = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._policy_initialized:
            self._init_policy()

        self._update_progress()

        try:
            remaining = float(self.task_duration) - float(self._total_done)
        except Exception:
            remaining = 0.0
        if remaining <= 0.0:
            # Task already completed: don't spend more.
            return ClusterType.NONE

        try:
            elapsed = float(self.env.elapsed_seconds)
        except Exception:
            elapsed = 0.0
        try:
            deadline = float(self.deadline)
        except Exception:
            deadline = elapsed

        time_left = deadline - elapsed
        if time_left <= 0.0:
            # Already at/after deadline; still try to make progress as fast as possible.
            return ClusterType.ON_DEMAND

        try:
            overhead = float(self.restart_overhead)
        except Exception:
            overhead = 0.0

        # F is the slack if we were to immediately switch to OD (including one restart_overhead).
        F = time_left - (remaining + overhead)

        # If we've committed to on-demand for the rest of the run, always use it.
        if self._final_od_commit:
            return ClusterType.ON_DEMAND

        # If slack is too small, permanently switch to on-demand to guarantee finish.
        if F <= self.commit_threshold:
            self._final_od_commit = True
            return ClusterType.ON_DEMAND

        # Pre-commit phase: still have comfortable slack.
        if has_spot:
            # Prefer cheap spot instances whenever available in non-critical regime.
            return ClusterType.SPOT

        # No spot available this step.
        # If we have plenty of slack, we can afford to wait for spot.
        if F > self.wait_threshold:
            return ClusterType.NONE

        # Slack is moderate: use on-demand to maintain sufficient progress.
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)