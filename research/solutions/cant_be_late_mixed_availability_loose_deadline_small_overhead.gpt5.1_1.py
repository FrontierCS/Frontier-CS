from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except TypeError:
                pass
        self.args = args
        self._progress_index = 0
        self._progress_total = 0.0
        self._init_done = False
        self._initial_slack = 0.0
        self.high_slack = 0.0
        self.commit_slack = 0.0
        self.total_steps = 0
        self.spot_available_steps = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _maybe_init(self):
        if self._init_done:
            return

        # Basic values in seconds
        try:
            gap = float(getattr(self.env, "gap_seconds", 60.0))
        except Exception:
            gap = 60.0

        try:
            deadline = float(self.deadline)
        except Exception:
            deadline = 0.0

        try:
            task_duration = float(self.task_duration)
        except Exception:
            task_duration = 0.0

        try:
            restart_overhead = float(getattr(self, "restart_overhead", 0.0))
        except Exception:
            restart_overhead = 0.0

        initial_slack = max(0.0, deadline - task_duration)
        self._initial_slack = initial_slack

        if initial_slack <= 0.0:
            high_slack = 0.0
            commit_slack = 0.0
        else:
            # Base fractions of initial slack
            high_frac = 0.10   # 10% of initial slack
            commit_frac = 0.03  # 3% of initial slack

            high_slack = initial_slack * high_frac
            commit_slack = initial_slack * commit_frac

            # Absolute minimums (in seconds), scaled but not exceeding initial slack
            min_high = 1.5 * 3600.0  # 1.5 hours
            min_commit = 0.5 * 3600.0  # 0.5 hours

            high_slack = min(max(high_slack, min_high), 0.8 * initial_slack)
            commit_slack = min(max(commit_slack, min_commit), 0.5 * initial_slack)

            # Ensure commit threshold is not too close to high_slack
            commit_slack = min(commit_slack, high_slack * 0.75)

            # Add safety relative to overhead and step size
            commit_slack = max(commit_slack,
                               restart_overhead * 4.0,
                               gap * 6.0)
            high_slack = max(high_slack, commit_slack * 2.0)

            # Final clamping within [0, initial_slack]
            if initial_slack > 0.0:
                high_slack = min(high_slack, initial_slack)
                commit_slack = min(commit_slack, high_slack)
            else:
                high_slack = 0.0
                commit_slack = 0.0

        self.high_slack = high_slack
        self.commit_slack = commit_slack
        self._init_done = True

    def _update_progress(self):
        """Incrementally accumulate completed task work (in seconds)."""
        segs = getattr(self, "task_done_time", None)
        if not segs:
            return
        idx = self._progress_index
        n = len(segs)
        if idx >= n:
            return
        total = self._progress_total
        # Process only new segments
        for i in range(idx, n):
            seg = segs[i]
            try:
                if isinstance(seg, (tuple, list)) and len(seg) >= 2:
                    dur = float(seg[1]) - float(seg[0])
                else:
                    dur = float(seg)
            except Exception:
                continue
            if dur > 0.0:
                total += dur
        self._progress_total = total
        self._progress_index = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._maybe_init()
        self._update_progress()

        self.total_steps += 1
        if has_spot:
            self.spot_available_steps += 1

        # Basic timing
        try:
            t = float(self.env.elapsed_seconds)
        except Exception:
            t = 0.0

        try:
            time_left = float(self.deadline) - t
        except Exception:
            time_left = 0.0

        remaining_work = max(0.0, float(self.task_duration) - self._progress_total)

        # If no remaining work or no time left, no need to run anything.
        if remaining_work <= 0.0 or time_left <= 0.0:
            return ClusterType.NONE

        # Slack is how much wall-clock we can still waste (seconds)
        slack = time_left - remaining_work

        # If already behind schedule, best-effort is to run OD continuously.
        if slack <= 0.0:
            return ClusterType.ON_DEMAND

        # Thresholds
        high_slack = self.high_slack
        commit_slack = self.commit_slack

        try:
            gap = float(getattr(self.env, "gap_seconds", 60.0))
        except Exception:
            gap = 60.0
        try:
            restart_overhead = float(getattr(self, "restart_overhead", 0.0))
        except Exception:
            restart_overhead = 0.0

        # Spot-stop threshold: below this slack we stop using spot even if available
        spot_stop = max(commit_slack * 2.0,
                        commit_slack + 3.0 * restart_overhead,
                        commit_slack + 4.0 * gap)
        if spot_stop > high_slack:
            spot_stop = high_slack

        # Phase logic:
        # 1) Very safe: slack > high_slack -> wait for spot, idle otherwise.
        if slack > high_slack:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE

        # 2) Moderate slack: high_slack >= slack > spot_stop
        #    Use spot when available, else OD (no more idling).
        if slack > spot_stop:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

        # 3) Low slack: spot_stop >= slack > commit_slack
        #    Do not risk further spot preemptions; stick to OD.
        if slack > commit_slack:
            return ClusterType.ON_DEMAND

        # 4) Very low slack: commit to pure OD to avoid any further risk.
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)