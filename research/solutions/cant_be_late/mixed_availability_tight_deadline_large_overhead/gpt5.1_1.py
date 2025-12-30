from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    # Slack thresholds in hours (converted to seconds in __init__)
    SLACK_IDLE_TO_OD_HOURS = 2.0       # When remaining slack <= 2h, stop idling; use OD when no spot
    SLACK_COMMIT_OD_ONLY_HOURS = 1.0   # When remaining slack <= 1h, commit to OD only

    def __init__(self, args):
        super().__init__(args)
        # Progress tracking
        self._progress_seconds = 0.0
        self._last_task_done_len = 0

        # Control flags
        self._committed_to_od = False

        # Cached thresholds in seconds (initialized lazily when env is available)
        self._slack_idle_to_od = None
        self._slack_commit_od_only = None

        # Step statistics (optional, could be used for adaptation)
        self._total_steps = 0
        self._spot_available_steps = 0

    def solve(self, spec_path: str) -> "Solution":
        # No offline preprocessing needed for now.
        return self

    # --- Internal helpers -------------------------------------------------

    def _init_thresholds_if_needed(self):
        if self._slack_idle_to_od is None or self._slack_commit_od_only is None:
            hour = 3600.0
            self._slack_idle_to_od = self.SLACK_IDLE_TO_OD_HOURS * hour
            self._slack_commit_od_only = self.SLACK_COMMIT_OD_ONLY_HOURS * hour

    def _segment_duration(self, seg) -> float:
        """Best-effort extraction of compute duration from a segment object."""
        try:
            # Numeric duration directly
            if isinstance(seg, (int, float)):
                v = float(seg)
                return v if v > 0.0 else 0.0

            # Tuple/list: likely [start, end]
            if isinstance(seg, (list, tuple)) and len(seg) >= 2:
                s = float(seg[0])
                e = float(seg[1])
                return (e - s) if e > s else 0.0

            # Object with attributes start/end or similar
            start = None
            end = None
            if hasattr(seg, "start") and hasattr(seg, "end"):
                start = getattr(seg, "start")
                end = getattr(seg, "end")
            elif hasattr(seg, "t_start") and hasattr(seg, "t_end"):
                start = getattr(seg, "t_start")
                end = getattr(seg, "t_end")

            if start is not None and end is not None:
                s = float(start)
                e = float(end)
                return (e - s) if e > s else 0.0
        except Exception:
            pass

        return 0.0

    def _update_progress(self):
        """Incrementally update total compute progress from new task_done_time segments."""
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return

        n = len(segments)
        if n <= self._last_task_done_len:
            return

        for i in range(self._last_task_done_len, n):
            self._progress_seconds += self._segment_duration(segments[i])
        self._last_task_done_len = n

        # Never exceed declared task duration
        if hasattr(self, "task_duration"):
            if self._progress_seconds > self.task_duration:
                self._progress_seconds = float(self.task_duration)

    # --- Core decision logic ----------------------------------------------

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_thresholds_if_needed()
        self._update_progress()

        self._total_steps += 1
        if has_spot:
            self._spot_available_steps += 1

        # Basic environment quantities
        elapsed = float(self.env.elapsed_seconds)
        gap = float(self.env.gap_seconds)
        time_left = float(self.deadline) - elapsed
        if time_left < 0.0:
            time_left = 0.0

        remaining_work = max(float(self.task_duration) - self._progress_seconds, 0.0)

        # Remaining slack = time we can still "waste" (idle + overhead) and still finish on time
        slack = time_left - remaining_work

        # If we've already decided to commit to OD, keep using it.
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # If slack is negative, we're already late; best we can do is use OD.
        if slack <= 0.0:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Hard safety condition: if we are close enough to the deadline that only OD
        # can possibly save us, commit to OD now.
        required_time_if_commit_now = float(self.restart_overhead) + remaining_work
        # Add a small safety margin of a few steps
        safety_margin = 3.0 * gap
        if time_left <= required_time_if_commit_now + safety_margin:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Soft slack-based thresholds
        slack_idle_to_od = self._slack_idle_to_od
        slack_commit_od_only = self._slack_commit_od_only

        # Commit to OD-only when slack is low enough; avoid any further spot risk.
        if slack <= slack_commit_od_only:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # When slack is moderate or low but above commit threshold,
        # ensure we don't idle: use OD if spot is unavailable.
        if slack <= slack_idle_to_od:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

        # High-slack regime: we can afford to wait for spot.
        if has_spot:
            return ClusterType.SPOT

        # Plenty of slack and no spot: pause to save cost.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)