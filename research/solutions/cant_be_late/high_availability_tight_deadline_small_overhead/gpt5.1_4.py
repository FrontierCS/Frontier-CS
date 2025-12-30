from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args):
        super().__init__(args)
        self.commit_on_demand = False
        self._params_inited = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _init_params_if_needed(self):
        if self._params_inited:
            return
        self._params_inited = True

        # Initial slack (seconds)
        try:
            slack0 = max(float(self.deadline) - float(self.task_duration), 0.0)
        except Exception:
            slack0 = 0.0

        try:
            dt = float(getattr(self.env, "gap_seconds", 60.0)) or 60.0
        except Exception:
            dt = 60.0

        try:
            rh = float(getattr(self, "restart_overhead", 0.0)) or 0.0
        except Exception:
            rh = 0.0

        # Commit threshold: when slack drops below this, permanently switch to on-demand.
        if slack0 > 0.0:
            base_commit = 0.1 * slack0  # 10% of total slack
        else:
            base_commit = 0.0
        commit_slack = max(base_commit, 4.0 * rh, 3.0 * dt)
        if slack0 > 0.0:
            commit_slack = min(commit_slack, 0.5 * slack0)
        if commit_slack <= 0.0:
            commit_slack = rh + dt if (rh + dt) > 0.0 else 1.0

        # Idle threshold: while slack > idle_slack, we are allowed to pause when spot is unavailable.
        if slack0 > 0.0:
            base_idle = 0.3 * slack0  # 30% of total slack
        else:
            base_idle = 0.0
        idle_slack = max(base_idle, commit_slack + 4.0 * rh, 6.0 * dt)
        if slack0 > 0.0:
            idle_slack = min(idle_slack, 0.9 * slack0)  # keep some slack always
        if idle_slack < commit_slack:
            idle_slack = commit_slack

        self._slack0 = slack0
        self._commit_slack = commit_slack
        self._idle_slack = idle_slack

    def _compute_progress(self):
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return 0.0
        total = 0.0
        for seg in segments:
            try:
                s, e = seg
            except Exception:
                # Fallback if segment is an object with attributes
                s = getattr(seg, "start", 0.0)
                e = getattr(seg, "end", 0.0)
            if e > s:
                total += (e - s)
        return total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_params_if_needed()

        # Compute current progress and slack
        progress = self._compute_progress()
        remaining = max(self.task_duration - progress, 0.0)

        # If somehow called after completion, do nothing.
        if remaining <= 0.0:
            return ClusterType.NONE

        current_time = float(self.env.elapsed_seconds)
        time_left = max(self.deadline - current_time, 0.0)
        slack = time_left - remaining

        # Safety: if we're tight on slack or already committed, use on-demand only.
        if self.commit_on_demand or slack <= self._commit_slack:
            self.commit_on_demand = True
            return ClusterType.ON_DEMAND

        # Pre-commit phase.
        if has_spot:
            # Spot available and we still have comfortable slack: use spot.
            return ClusterType.SPOT

        # No spot available: decide between pausing and using on-demand.
        if slack > self._idle_slack:
            # Plenty of slack remaining: we can afford to wait for spot to return.
            return ClusterType.NONE

        # Slack getting tighter: fall back to on-demand while spot is unavailable.
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)