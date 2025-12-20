import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_threshold_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self._thresholds_initialized = False
        self.urgent_slack_threshold = None
        self.idle_slack_threshold = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _initialize_thresholds_if_needed(self):
        if self._thresholds_initialized:
            return

        # Initial slack = time budget minus required work (in seconds).
        initial_slack = max(self.deadline - self.task_duration, 0.0)

        # Use fractions of initial slack, but also tie to restart_overhead for robustness.
        # Urgent: when slack is very small, always use OD (even if spot is available).
        # Idle: when slack is large and no spot, we can pause instead of paying for OD.
        urgent_from_slack = 0.10 * initial_slack  # 10% of slack
        urgent_from_overhead = 3.0 * self.restart_overhead
        urgent = max(urgent_from_slack, urgent_from_overhead)

        idle_from_slack = 0.40 * initial_slack  # 40% of slack
        idle_min_gap = urgent + 5.0 * self.restart_overhead
        idle = max(idle_from_slack, idle_min_gap)

        # Ensure ordering and non-negativity.
        if idle < urgent:
            idle = urgent + 2.0 * self.restart_overhead

        self.urgent_slack_threshold = urgent
        self.idle_slack_threshold = idle
        self._thresholds_initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_thresholds_if_needed()

        # Basic time accounting
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed

        # Sum of completed work segments (seconds of effective compute).
        done_segments = self.task_done_time or []
        work_done = sum(done_segments)

        remaining_work = self.task_duration - work_done
        if remaining_work <= 0:
            # Task completed; no need to run anything.
            return ClusterType.NONE

        # Slack = time_left - work_remaining (seconds).
        slack = time_left - remaining_work

        # If we are already at/past deadline or slack is very small/negative, must use OD.
        # This is also captured by urgent_slack_threshold since it's positive.
        if slack <= self.urgent_slack_threshold:
            return ClusterType.ON_DEMAND

        # Non-urgent zone: we have decent slack.
        if has_spot:
            # When spot is available and we are not in urgent zone, prefer SPOT.
            return ClusterType.SPOT

        # No spot available.
        # If slack is still large, we can afford to wait for cheaper spot (NONE).
        if slack > self.idle_slack_threshold:
            return ClusterType.NONE

        # Slack is moderate: can't idle further; use OD to make progress.
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
