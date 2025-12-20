import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_safe_latest_commit_v2"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except TypeError:
                pass
        self._od_committed = False
        self._spec_path = None
        self._steps = 0
        self._steps_spot_available = 0

    def solve(self, spec_path: str) -> "Solution":
        self._spec_path = spec_path
        return self

    def _remaining_work(self) -> float:
        try:
            done_list = getattr(self, "task_done_time", None)
            if done_list is None:
                return float(getattr(self, "task_duration", 0.0))
            done = float(sum(done_list))
        except Exception:
            done = float(sum(getattr(self, "task_done_time", []))) if hasattr(self, "task_done_time") else 0.0
        rem = float(getattr(self, "task_duration", 0.0)) - done
        if rem < 0.0:
            rem = 0.0
        return rem

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._steps += 1
        if has_spot:
            self._steps_spot_available += 1

        if self._od_committed:
            return ClusterType.ON_DEMAND

        t = float(getattr(self.env, "elapsed_seconds", 0.0))
        dt = float(getattr(self.env, "gap_seconds", 60.0))
        deadline = float(getattr(self, "deadline", t + 3600.0))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))
        remaining_work = self._remaining_work()

        commit_latest = deadline - (restart_overhead + remaining_work)
        eps = 1e-9

        if (t >= commit_latest - eps) or (t + dt > commit_latest + eps):
            self._od_committed = True
            return ClusterType.ON_DEMAND

        if has_spot:
            time_until_commit = commit_latest - t
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            else:
                min_window = restart_overhead + dt
                if time_until_commit > min_window + eps:
                    return ClusterType.SPOT
                else:
                    return ClusterType.NONE
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        try:
            args, _ = parser.parse_known_args()
        except Exception:
            args = None
        return cls(args)
