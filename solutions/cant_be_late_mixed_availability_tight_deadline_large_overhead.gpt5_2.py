from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_guarded_spot_then_fallback"

    def solve(self, spec_path: str) -> "Solution":
        # Initialize internal state
        self._started_od = False  # Once we switch to OD, we stick with it
        self._avail_time = 0.0
        self._unavail_time = 0.0
        self._current_unavail_streak = 0.0
        return self

    def _remaining_compute_seconds(self) -> float:
        gap = getattr(self.env, "gap_seconds", 1.0)
        done_segments = len(getattr(self, "task_done_time", []))
        done_time = done_segments * gap
        remaining = max(0.0, float(getattr(self, "task_duration", 0.0)) - done_time)
        return remaining

    def _time_left_seconds(self) -> float:
        return float(getattr(self, "deadline", 0.0)) - float(getattr(self.env, "elapsed_seconds", 0.0))

    def _dynamic_safety_margin(self, has_spot: bool) -> float:
        # Base safety margin accounts for discretization and restart overhead
        gap = float(getattr(self.env, "gap_seconds", 60.0))
        overhead = float(getattr(self, "restart_overhead", 0.0))
        # Base: two steps + 20% overhead + 60s buffer
        base_margin = max(2.0 * gap, 1.2 * overhead + 60.0)

        total_obs = self._avail_time + self._unavail_time
        if total_obs > 0:
            avail_ratio = self._avail_time / total_obs
        else:
            avail_ratio = 1.0  # optimistic at the start

        # Increase margin if observed availability is poor
        scarcity_multiplier = 1.0
        if avail_ratio < 0.5:
            scarcity_multiplier += 0.25
        if avail_ratio < 0.3:
            scarcity_multiplier += 0.25

        # Add a fraction of the current unavailable streak to be more conservative during long outages
        # Cap added margin to 30 minutes
        streak_bonus = min(self._current_unavail_streak * 0.25, 1800.0)

        return base_margin * scarcity_multiplier + streak_bonus

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        gap = float(getattr(self.env, "gap_seconds", 60.0))

        # Update availability statistics with current step
        if has_spot:
            self._avail_time += gap
            self._current_unavail_streak = 0.0
        else:
            self._unavail_time += gap
            self._current_unavail_streak += gap

        # If we've already started on-demand, keep using it to avoid extra overheads and guarantee deadline.
        if self._started_od or last_cluster_type == ClusterType.ON_DEMAND:
            self._started_od = True
            return ClusterType.ON_DEMAND

        # Compute remaining work and time left
        remaining = self._remaining_compute_seconds()
        if remaining <= 0.0:
            # Job done; no need to run any more
            return ClusterType.NONE

        time_left = self._time_left_seconds()
        if time_left <= 0.0:
            # Already at/after deadline; pick OD to attempt minimal lateness
            self._started_od = True
            return ClusterType.ON_DEMAND

        # Determine if we must switch to OD to safely meet deadline.
        # If we start OD now, we will incur one restart overhead (since we're not on OD).
        overhead_if_starting_od = float(getattr(self, "restart_overhead", 0.0))
        # Slack if we defer OD further
        slack = time_left - (remaining + overhead_if_starting_od)

        safety_margin = self._dynamic_safety_margin(has_spot)

        # If slack is small, commit to on-demand immediately
        if slack <= safety_margin:
            self._started_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, prefer spot when available, else wait
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
