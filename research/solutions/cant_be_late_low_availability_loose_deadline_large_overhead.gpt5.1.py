from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self.args = args

        # Statistics (not strictly needed for core logic but useful for extensions)
        self.total_steps = 0
        self.spot_available_steps = 0
        self.spot_used_steps = 0
        self.on_demand_steps = 0
        self.idle_steps = 0

        # Scheduling parameters (set lazily once env is available)
        self.initial_slack = None
        self.commit_slack_seconds = None  # slack threshold to switch to always-on on-demand
        self.no_idle_slack_seconds = None  # below this slack we never idle when no spot

    def solve(self, spec_path: str) -> "Solution":
        # No offline preprocessing; just return self.
        return self

    def _init_thresholds_if_needed(self):
        """Initialize slack-based thresholds once env is available."""
        if self.commit_slack_seconds is None:
            # restart_overhead is in seconds; add a safety margin.
            overhead = getattr(self, "restart_overhead", 0.0) or 0.0
            # Commit threshold: at least 1 hour, and at least 2 * overhead + 30 minutes
            self.commit_slack_seconds = max(3600.0, 2.0 * overhead + 1800.0)

        if self.no_idle_slack_seconds is None:
            # Stop idling (run OD when no spot) once slack <= 8 hours.
            self.no_idle_slack_seconds = 8.0 * 3600.0

    def _compute_done_seconds(self) -> float:
        """Robustly compute total completed task duration from task_done_time."""
        done = 0.0
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return 0.0
        for seg in segments:
            try:
                if seg is None:
                    continue
                # Simple numeric duration
                if isinstance(seg, (int, float)):
                    done += float(seg)
                # Interval [start, end]
                elif isinstance(seg, (list, tuple)) and len(seg) >= 2:
                    start, end = seg[0], seg[1]
                    dur = float(end) - float(start)
                    if dur > 0:
                        done += dur
                else:
                    # Fallback: try to treat as scalar duration
                    done += float(seg)
            except Exception:
                # Ignore malformed entries
                continue
        return done

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize thresholds based on environment parameters if needed
        self._init_thresholds_if_needed()

        self.total_steps += 1
        if has_spot:
            self.spot_available_steps += 1

        # Compute remaining work and slack
        done_seconds = self._compute_done_seconds()
        remaining_work = max(self.task_duration - done_seconds, 0.0)

        elapsed = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
        remaining_time = max(self.deadline - elapsed, 0.0)

        slack = remaining_time - remaining_work  # positive means ahead of schedule

        if self.initial_slack is None:
            self.initial_slack = slack

        # Hard safety: if slack is small (or negative due to rounding), use on-demand only.
        if slack <= self.commit_slack_seconds:
            self.on_demand_steps += 1
            return ClusterType.ON_DEMAND

        # Slack is healthy (> commit_slack_seconds)
        # Prefer spot whenever available (it's cheaper and we still have buffer).
        if has_spot:
            self.spot_used_steps += 1
            return ClusterType.SPOT

        # No spot available this step.
        # Idle only if we have plenty of slack; otherwise, fall back to on-demand.
        if slack > self.no_idle_slack_seconds:
            self.idle_steps += 1
            return ClusterType.NONE

        self.on_demand_steps += 1
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)