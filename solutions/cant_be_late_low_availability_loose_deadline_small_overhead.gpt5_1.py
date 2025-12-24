import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_slack_guard_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self._commit_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work(self) -> float:
        try:
            done = sum(self.task_done_time) if self.task_done_time is not None else 0.0
        except Exception:
            done = 0.0
        rem = self.task_duration - done
        if rem < 0:
            rem = 0.0
        return rem

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self._commit_to_od or last_cluster_type == ClusterType.ON_DEMAND:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        rem = self._remaining_work()
        if rem <= 0:
            return ClusterType.NONE

        t_now = getattr(self.env, "elapsed_seconds", 0.0)
        deadline = getattr(self, "deadline", None)
        if deadline is None:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND
        time_left = deadline - t_now
        if time_left < 0:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        overhead = getattr(self, "restart_overhead", 0.0)
        eps = 1e-9

        if has_spot:
            if time_left + eps >= rem + overhead:
                return ClusterType.SPOT
            else:
                self._commit_to_od = True
                return ClusterType.ON_DEMAND
        else:
            if time_left - eps > rem + overhead:
                return ClusterType.NONE
            else:
                self._commit_to_od = True
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
