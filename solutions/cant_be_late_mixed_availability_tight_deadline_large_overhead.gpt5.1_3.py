import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v1"

    def __init__(self, args):
        super().__init__(args)
        self._policy_initialized = False
        self._slack_total = None
        self._commit_slack = None
        self._idle_slack_threshold = None
        self._od_only = False

        # Caching for task_done_time parsing
        self._cached_tdt_len = 0
        self._cached_work_done = 0.0

    def solve(self, spec_path: str) -> "Solution":
        # No pre-computation needed; all done lazily in _step
        return self

    # ---------------- Policy helpers ---------------- #

    def _init_policy_params(self):
        # Initialize once environment and task parameters are available
        if self._policy_initialized:
            return

        # Total slack: how much wall-clock we can waste
        # Note: deadline and task_duration are seconds from env
        self._slack_total = max(float(self.deadline) - float(self.task_duration), 0.0)

        # Time step size
        gap = getattr(self.env, "gap_seconds", 60.0)
        gap = float(gap)

        # Restart overhead (seconds)
        overhead = float(getattr(self, "restart_overhead", 0.0))

        # When remaining slack falls below this, permanently switch to ON_DEMAND
        # Base on a couple of restart overheads plus some discretization margin
        base_commit = 2.0 * overhead + 5.0 * gap

        # Also ensure at least a small fraction of total slack for robustness
        frac_commit = 0.1 * self._slack_total
        self._commit_slack = min(max(base_commit, frac_commit), self._slack_total)

        # Threshold above which we are willing to idle (NONE) when spot is unavailable
        # Prefer to spend up to about half of the total slack on idling early on.
        idle_frac = 0.5
        self._idle_slack_threshold = min(self._slack_total * idle_frac, self._slack_total)

        # Ensure we stop idling before we hit the commit threshold
        if self._idle_slack_threshold < self._commit_slack + 2.0 * gap:
            self._idle_slack_threshold = min(self._slack_total, self._commit_slack + 2.0 * gap)

        self._policy_initialized = True

    # ---- Task progress computation helpers ---- #

    def _segment_duration(self, seg):
        """Robustly extract duration (in seconds) from a task_done_time segment."""
        if seg is None:
            return 0.0
        # Numeric: treat as already a duration
        if isinstance(seg, (int, float)):
            return float(seg)
        # (start, end) tuple/list
        if isinstance(seg, (list, tuple)) and len(seg) >= 2:
            start, end = seg[0], seg[1]
            if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                return max(float(end) - float(start), 0.0)
            return 0.0
        # Dict with start/end keys
        if isinstance(seg, dict):
            start = seg.get("start", 0.0)
            end = seg.get("end", 0.0)
            if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                return max(float(end) - float(start), 0.0)
            return 0.0
        # Fallback: unknown structure
        return 0.0

    def _compute_work_done(self):
        """Compute total completed work (seconds) from self.task_done_time."""
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0

        # If task_done_time is already numeric
        if isinstance(tdt, (int, float)):
            return min(float(tdt), float(self.task_duration))

        # If it's a list, we can cache partial sums
        if isinstance(tdt, list):
            n = len(tdt)
            # If list shrunk or reset, recompute from scratch
            if n < self._cached_tdt_len:
                self._cached_tdt_len = 0
                self._cached_work_done = 0.0
            # Accumulate new segments
            for i in range(self._cached_tdt_len, n):
                self._cached_work_done += self._segment_duration(tdt[i])
            self._cached_tdt_len = n
            return min(self._cached_work_done, float(self.task_duration))

        # Fallback: iterate over whatever iterable structure it is
        total = 0.0
        try:
            for seg in tdt:
                total += self._segment_duration(seg)
        except TypeError:
            # Not iterable; ignore
            pass
        return min(total, float(self.task_duration))

    # ---------------- Core step logic ---------------- #

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize thresholds on first step where env is ready
        if not self._policy_initialized:
            self._init_policy_params()

        # Basic environment values
        env = self.env
        elapsed = float(getattr(env, "elapsed_seconds", 0.0))
        gap = float(getattr(env, "gap_seconds", 60.0))
        deadline = float(self.deadline)

        # Compute remaining work
        work_done = self._compute_work_done()
        remaining_work = max(float(self.task_duration) - work_done, 0.0)

        # If work is done, no need to run more
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Time left until deadline
        time_left = deadline - elapsed

        # Slack = time left - work left (assuming perfect future on-demand usage)
        slack = time_left - remaining_work

        # If we've already exhausted slack (or negative due to rounding),
        # force ON_DEMAND; may still be too late but that's best effort.
        if slack <= 0.0:
            self._od_only = True
        else:
            # If slack is small, permanently switch to ON_DEMAND
            if (not self._od_only) and slack <= self._commit_slack:
                self._od_only = True

        # Once we commit to on-demand only, never go back to spot
        if self._od_only:
            return ClusterType.ON_DEMAND

        # Not OD-only yet: opportunistic phase

        # If spot available, always prefer it during this phase
        if has_spot:
            return ClusterType.SPOT

        # No spot available: decide between idling and on-demand
        # If we have plenty of slack above idle_slack_threshold, we can afford to wait.
        if slack > self._idle_slack_threshold + gap:
            return ClusterType.NONE

        # Slack is getting tighter; use on-demand while waiting for spot
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
