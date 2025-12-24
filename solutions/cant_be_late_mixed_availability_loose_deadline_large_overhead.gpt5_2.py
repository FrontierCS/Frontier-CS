from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_robust_od_commit"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args
        self._commit_od = False
        self._od_commit_time = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _should_commit_to_od(self, last_cluster_type: ClusterType) -> bool:
        # Compute remaining work and time
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining_work = max(self.task_duration - done, 0.0)

        elapsed = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
        deadline = getattr(self, "deadline", 0.0) or 0.0
        time_remaining = max(deadline - elapsed, 0.0)

        gap = getattr(self.env, "gap_seconds", 60.0) or 60.0
        restart_overhead = getattr(self, "restart_overhead", 0.0) or 0.0

        # Fudge factor to account for discretization and any timing uncertainty
        fudge_seconds = max(2.0 * gap, min(restart_overhead, 900.0))  # at least 2 steps, cap fudge at 15 min

        # If we are already on on-demand, switching cost is zero; otherwise, we assume one restart overhead
        switch_overhead_to_od = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead

        # Commit if we don't have sufficient time slack to risk waiting anymore
        need_time_if_switch_now = remaining_work + switch_overhead_to_od
        return time_remaining <= (need_time_if_switch_now + fudge_seconds)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Reset per new episode
        if getattr(self.env, "elapsed_seconds", 0.0) == 0.0:
            self._commit_od = False
            self._od_commit_time = None

        # If task is complete, no need to run
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        if done >= self.task_duration:
            return ClusterType.NONE

        # If already committed to OD, stick with it
        if self._commit_od:
            return ClusterType.ON_DEMAND

        # Decide whether to commit to OD this step
        if self._should_commit_to_od(last_cluster_type):
            self._commit_od = True
            self._od_commit_time = getattr(self.env, "elapsed_seconds", None)
            return ClusterType.ON_DEMAND

        # Otherwise use SPOT if available; else wait (NONE)
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
