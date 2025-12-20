from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_commit_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            pass
        self._committed_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to on-demand, keep using it
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Gather environment info
        elapsed = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
        deadline = getattr(self, "deadline", 0.0) or 0.0
        restart_overhead = getattr(self, "restart_overhead", 0.0) or 0.0
        task_duration = getattr(self, "task_duration", 0.0) or 0.0
        done_list = getattr(self, "task_done_time", None)
        if done_list is None:
            done = 0.0
        else:
            try:
                done = float(sum(done_list))
            except Exception:
                done = 0.0

        remaining = max(task_duration - done, 0.0)
        time_left = max(deadline - elapsed, 0.0)
        # Conservative commit buffer to handle discrete steps and immediate preemptions
        commit_buffer = max(3.0 * gap, 1.5 * restart_overhead, 60.0)

        # Overhead if switching to on-demand now
        od_switch_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead

        # If we must commit to on-demand to safely finish, do it now
        if time_left <= remaining + od_switch_overhead + commit_buffer:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Prefer spot when available until we must commit
        if has_spot:
            return ClusterType.SPOT

        # No spot available and not yet time-critical: wait to save cost
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
