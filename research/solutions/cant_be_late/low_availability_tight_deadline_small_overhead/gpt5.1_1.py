from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_v1"

    IDLE_FRACTION = 0.7  # Fraction of non-committed slack we allow to spend on idling

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Scheduling state
        self.commit_od = False
        self.initial_slack = None  # Initial slack (seconds)
        self.commit_margin = 0.0   # Slack threshold at/under which we commit to OD-only
        self.idle_budget = 0.0     # Max time we allow ourselves to idle (seconds)
        self.idle_used = 0.0       # Idle time used so far (seconds)

        # Efficient tracking of task progress (sum of task_done_time segments)
        self._progress_sum = 0.0
        self._last_tdt_len = 0
        self._last_tdt_last = 0.0

    def solve(self, spec_path: str) -> "Solution":
        # Optional: could read spec_path if needed; we don't need it here.
        return self

    def _update_progress(self) -> float:
        """Efficiently track total completed work from self.task_done_time."""
        segments = self.task_done_time
        n = len(segments)

        if n == 0:
            # No completed segments
            self._progress_sum = 0.0
            self._last_tdt_len = 0
            self._last_tdt_last = 0.0
            return 0.0

        if self._last_tdt_len == 0:
            # First time seeing non-empty list: sum everything
            total = 0.0
            for v in segments:
                total += v
            self._progress_sum = total
        elif n < self._last_tdt_len:
            # List shrank (e.g., environment adjusted segments significantly) – recompute
            total = 0.0
            for v in segments:
                total += v
            self._progress_sum = total
        elif n > self._last_tdt_len:
            # New segments appended – sum only the new part
            add = 0.0
            for i in range(self._last_tdt_len, n):
                add += segments[i]
            self._progress_sum += add
        else:
            # Same number of segments; only last element may have changed
            last_val = segments[-1]
            self._progress_sum += last_val - self._last_tdt_last

        self._last_tdt_len = n
        self._last_tdt_last = segments[-1]
        return self._progress_sum

    def _initialize_slack(self, time_left: float, remaining: float):
        """Initialize slack-related parameters on first step."""
        self.initial_slack = max(time_left - remaining, 0.0)

        # Maximum possible per-step slack loss: step duration + restart_overhead
        gap = self.env.gap_seconds
        restart_overhead = getattr(self, "restart_overhead", 0.0)
        delta_max = gap + restart_overhead

        if self.initial_slack <= 0.0:
            # No slack at all: must effectively run OD-only from the start
            self.commit_margin = 0.0
            self.idle_budget = 0.0
            return

        # Choose commit_margin:
        # - At least 2 * delta_max to avoid overshooting below zero slack in one step
        # - Roughly 25% of initial slack, but not more than 90% of it
        approx_margin = self.initial_slack * 0.25
        raw_margin = approx_margin if approx_margin > 2.0 * delta_max else 2.0 * delta_max
        max_margin = self.initial_slack * 0.9
        if raw_margin > max_margin:
            raw_margin = max_margin
        self.commit_margin = raw_margin

        # Remaining slack we can "spend" before commit is initial_slack - commit_margin.
        # We allow a fraction of that to be consumed purely by idling.
        remaining_slack_for_waste = self.initial_slack - self.commit_margin
        if remaining_slack_for_waste < 0.0:
            remaining_slack_for_waste = 0.0
        self.idle_budget = remaining_slack_for_waste * self.IDLE_FRACTION

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = self.env

        # Update completed work and compute remaining task duration
        work_done = self._update_progress()
        remaining = max(self.task_duration - work_done, 0.0)
        time_left = self.deadline - env.elapsed_seconds

        # If task is already finished (defensive check), don't run more
        if remaining <= 0.0:
            return ClusterType.NONE

        # If we are already past the deadline, just use OD to minimize further delay
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        # Lazily initialize slack / margin / idle budget on first step
        if self.initial_slack is None:
            self._initialize_slack(time_left, remaining)

        # Current slack: how much time we can afford to lose vs. ideal OD-only from now
        slack_now = time_left - remaining

        # If we've essentially exhausted slack (or gone negative), commit immediately
        if not self.commit_od:
            if slack_now <= self.commit_margin or slack_now <= 0.0:
                self.commit_od = True

        # Once committed, always use on-demand to guarantee no further overhead/idling
        if self.commit_od:
            return ClusterType.ON_DEMAND

        # Pre-commit region: decide between SPOT, OD, or NONE

        # 1. Prefer SPOT whenever available (cheapest), while we still have slack
        if has_spot:
            return ClusterType.SPOT

        # 2. Spot is unavailable; consider idling vs. on-demand

        # We can idle only if:
        #   - We haven't exceeded idle_budget
        #   - After idling for one more step, slack will still be >= commit_margin
        can_idle = False
        if self.idle_budget > 0.0 and self.idle_used < self.idle_budget:
            projected_slack_after_idle = slack_now - env.gap_seconds
            if projected_slack_after_idle >= self.commit_margin:
                can_idle = True

        if can_idle:
            self.idle_used += env.gap_seconds
            return ClusterType.NONE

        # 3. Otherwise, use on-demand to avoid burning more slack
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)