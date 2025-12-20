from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "jit_od_commit_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self._commit_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Compute remaining work
        done = 0.0
        try:
            if self.task_done_time:
                done = float(sum(self.task_done_time))
        except Exception:
            done = 0.0

        remaining_work = max(float(self.task_duration) - done, 0.0)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Time left to deadline
        time_left = float(self.deadline) - float(self.env.elapsed_seconds)

        # If we've already started OD, stay on OD to avoid extra restarts
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._commit_od = True

        # Estimate time needed on OD to finish if we switch now (include one restart overhead if switching from non-OD)
        od_start_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else float(self.restart_overhead)

        # Fudge factor to account for step granularity and minor uncertainties
        fudge_time = float(self.env.gap_seconds) + float(self.restart_overhead)

        # Decide whether to commit to OD to guarantee completion
        required_time_on_od = remaining_work + od_start_overhead
        threshold = required_time_on_od + fudge_time
        if not self._commit_od and time_left <= threshold:
            self._commit_od = True

        # If committed, always use on-demand
        if self._commit_od:
            return ClusterType.ON_DEMAND

        # Otherwise, prefer spot if available, else wait
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
