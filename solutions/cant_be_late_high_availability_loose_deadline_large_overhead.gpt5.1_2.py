from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cb_late_heuristic_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except TypeError:
                pass
        self._committed_to_on_demand = False

    def solve(self, spec_path: str) -> "Solution":
        self._committed_to_on_demand = False
        return self

    def _estimate_progress(self) -> float:
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return 0.0
        try:
            first = segments[0]
        except Exception:
            return 0.0

        if isinstance(first, (tuple, list)):
            total = 0.0
            for seg in segments:
                try:
                    if len(seg) >= 2:
                        s = float(seg[0])
                        e = float(seg[1])
                        if e > s:
                            total += e - s
                except Exception:
                    continue
            try:
                td = float(self.task_duration)
                if total > td:
                    total = td
            except Exception:
                pass
            if total < 0.0:
                total = 0.0
            return total
        else:
            maxv = None
            for x in segments:
                try:
                    fx = float(x)
                except Exception:
                    continue
                if maxv is None or fx > maxv:
                    maxv = fx
            if maxv is None:
                return 0.0
            if maxv < 0.0:
                maxv = 0.0
            try:
                td = float(self.task_duration)
                if maxv > td:
                    maxv = td
            except Exception:
                pass
            return maxv

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 0.0))
        deadline = float(getattr(self, "deadline", 0.0))
        task_duration = float(getattr(self, "task_duration", 0.0))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))

        time_left = deadline - elapsed
        if time_left < 0.0:
            time_left = 0.0

        work_done = self._estimate_progress()
        remaining_work = task_duration - work_done
        if remaining_work < 0.0:
            remaining_work = 0.0

        if not self._committed_to_on_demand:
            commit_threshold = remaining_work + restart_overhead + gap
            if time_left <= commit_threshold:
                self._committed_to_on_demand = True

        if self._committed_to_on_demand:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
