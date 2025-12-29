from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_lock_od"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self._locked_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self._locked_od:
            return ClusterType.ON_DEMAND

        try:
            if isinstance(self.task_done_time, (list, tuple)):
                done = float(sum(self.task_done_time))
            elif self.task_done_time is None:
                done = 0.0
            else:
                done = float(self.task_done_time)
        except Exception:
            done = 0.0

        remaining = max(self.task_duration - done, 0.0)
        time_left = max(self.deadline - self.env.elapsed_seconds, 0.0)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        required_if_fallback_now = remaining + float(self.restart_overhead or 0.0)

        # Commit to on-demand when we cannot afford another idle step.
        if time_left <= required_if_fallback_now + gap:
            self._locked_od = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)