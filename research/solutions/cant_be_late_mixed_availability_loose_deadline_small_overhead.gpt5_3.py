from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "robust_deadline_guard"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except Exception:
            pass
        self._committed_to_od = False
        self._cached_done_sum = 0.0
        self._cached_done_len = 0
        self._last_tdt_obj_id = None

    def solve(self, spec_path: str) -> "Solution":
        self._committed_to_od = False
        self._cached_done_sum = 0.0
        self._cached_done_len = 0
        self._last_tdt_obj_id = None
        return self

    def _safe_sum_task_done(self) -> float:
        tdt = getattr(self, 'task_done_time', None)
        if tdt is None:
            return 0.0
        if isinstance(tdt, (int, float)):
            try:
                return float(tdt)
            except Exception:
                return 0.0
        try:
            if isinstance(tdt, list):
                obj_id = id(tdt)
                if obj_id != self._last_tdt_obj_id:
                    self._last_tdt_obj_id = obj_id
                    self._cached_done_sum = 0.0
                    self._cached_done_len = 0
                n = len(tdt)
                if n > self._cached_done_len:
                    for i in range(self._cached_done_len, n):
                        self._cached_done_sum += float(tdt[i])
                    self._cached_done_len = n
                elif n < self._cached_done_len:
                    self._cached_done_sum = sum(float(x) for x in tdt)
                    self._cached_done_len = n
                return self._cached_done_sum
            elif isinstance(tdt, tuple):
                return float(sum(tdt))
            else:
                return float(sum(tdt))
        except Exception:
            try:
                return float(sum(tdt))
            except Exception:
                try:
                    return float(tdt)
                except Exception:
                    return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = getattr(self.env, 'elapsed_seconds', 0.0)
        gap = getattr(self.env, 'gap_seconds', 60.0)
        if gap <= 0:
            gap = 60.0
        deadline = getattr(self, 'deadline', 0.0)
        overhead = getattr(self, 'restart_overhead', 0.0)
        total_duration = getattr(self, 'task_duration', 0.0)

        done = self._safe_sum_task_done()
        remain = total_duration - done
        if remain <= 0.0:
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0.0:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        slack = time_left - remain

        safety_fudge = max(60.0, 0.1 * gap)
        guard = overhead + 2.0 * gap + safety_fudge

        if not self._committed_to_od and slack <= guard:
            self._committed_to_od = True

        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if slack - gap <= guard:
            return ClusterType.ON_DEMAND

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)