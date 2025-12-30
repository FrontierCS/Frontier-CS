from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_safe_wait_v1"

    def solve(self, spec_path: str) -> "Solution":
        self._commit_to_od = False
        return self

    def _sum_done(self) -> float:
        try:
            return float(sum(self.task_done_time)) if self.task_done_time else 0.0
        except Exception:
            return 0.0

    def _safety_buffer(self) -> float:
        # Reserve at least one step plus restart overhead as cushion
        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
        overhead = getattr(self, "restart_overhead", 0.0) or 0.0
        return gap + overhead

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we've already committed to on-demand, keep using it
        if getattr(self, "_commit_to_od", False):
            return ClusterType.ON_DEMAND

        # Compute remaining work and slack
        done = self._sum_done()
        task_duration = getattr(self, "task_duration", 0.0) or 0.0
        remaining_work = max(0.0, task_duration - done)

        # If work is done, pause
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Time left until deadline
        elapsed = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
        deadline = getattr(self, "deadline", 0.0) or 0.0
        time_left = deadline - elapsed

        # If somehow no time left, commit to OD to minimize further risk (though we're late)
        if time_left <= 0.0:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Slack = time left - compute left
        slack = time_left - remaining_work

        # Overhead if switching to on-demand now (zero if already on OD)
        restart_overhead = getattr(self, "restart_overhead", 0.0) or 0.0
        od_switch_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead

        # Safety buffer to account for discretization and overhead variability
        buffer = self._safety_buffer()

        # If slack is too small to safely wait any longer, commit to on-demand
        if slack <= (od_switch_overhead + buffer):
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, prefer spot when available; else wait
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)