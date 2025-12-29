from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_smart_v1"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Lazy initialization of internal state
        if not hasattr(self, "_internal_state_initialized"):
            self._internal_state_initialized = True
            self.committed_to_od = False
            self._last_seen_elapsed = -1.0

        elapsed = getattr(self.env, "elapsed_seconds", 0.0)

        # Detect new run (elapsed time reset)
        if elapsed < self._last_seen_elapsed:
            self.committed_to_od = False
        self._last_seen_elapsed = elapsed

        duration = float(self.task_duration)
        deadline = float(self.deadline)
        restart_overhead = float(self.restart_overhead)
        gap = float(self.env.gap_seconds)

        # Compute completed work
        segments = getattr(self, "task_done_time", None)
        if segments:
            completed = float(sum(segments))
        else:
            completed = 0.0

        remaining = max(duration - completed, 0.0)
        if remaining <= 0.0:
            # Task already finished
            return ClusterType.NONE

        time_left = deadline - elapsed
        total_slack = max(deadline - duration, 0.0)

        # Thresholds based on environment parameters
        # How far behind ideal schedule we allow before using OD when no spot (seconds of work)
        max_lag = 0.05 * total_slack
        if max_lag < max(restart_overhead, gap):
            max_lag = max(restart_overhead, gap)

        # Slack threshold at which we fully commit to on-demand (seconds of wall time)
        commit_slack = 0.1 * total_slack
        min_commit_slack = 2.0 * restart_overhead + 2.0 * gap
        if commit_slack < min_commit_slack:
            commit_slack = min_commit_slack

        slack_now = time_left - remaining

        # Commit to full on-demand when slack becomes small
        if not self.committed_to_od and slack_now <= commit_slack:
            self.committed_to_od = True

        if self.committed_to_od:
            return ClusterType.ON_DEMAND

        # Ideal schedule: linear progress to finish exactly at deadline
        if deadline > 0.0:
            required_rate = duration / deadline
        else:
            required_rate = 1.0

        required_done = required_rate * elapsed
        if required_done > duration:
            required_done = duration

        # Positive lag = behind schedule (in seconds of work)
        lag = required_done - completed

        if has_spot:
            # Prefer spot when available unless very close to needing full OD
            if slack_now < 0.5 * commit_slack:
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # No spot available: decide between on-demand and idling
        # Use on-demand if significantly behind or close enough to deadline that idling is risky
        if lag > max_lag or slack_now <= 3.0 * commit_slack:
            return ClusterType.ON_DEMAND
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)