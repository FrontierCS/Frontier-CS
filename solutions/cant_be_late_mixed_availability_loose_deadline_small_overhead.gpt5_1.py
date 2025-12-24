from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "safe_fallback_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args
        self._commit_to_od = False
        self._cached_done_sum = 0.0
        self._cached_done_len = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _segment_duration(self, seg):
        try:
            if isinstance(seg, (list, tuple)):
                if len(seg) >= 2:
                    a, b = seg[0], seg[1]
                    try:
                        return float(b) - float(a)
                    except Exception:
                        try:
                            return float(b)
                        except Exception:
                            return 0.0
                elif len(seg) == 1:
                    try:
                        return float(seg[0])
                    except Exception:
                        return 0.0
                else:
                    return 0.0
            else:
                return float(seg)
        except Exception:
            return 0.0

    def _get_work_remaining(self) -> float:
        total = 0.0
        try:
            total = float(self.task_duration)
        except Exception:
            total = 0.0

        lst = getattr(self, "task_done_time", []) or []
        # If list shrank or changed type, recompute from scratch
        if not isinstance(lst, list) or len(lst) < self._cached_done_len:
            self._cached_done_len = 0
            self._cached_done_sum = 0.0

        # Accumulate newly added segments
        n = len(lst)
        for i in range(self._cached_done_len, n):
            self._cached_done_sum += self._segment_duration(lst[i])

        self._cached_done_len = n
        done = max(0.0, min(self._cached_done_sum, total if total > 0 else self._cached_done_sum))
        remaining = max(0.0, total - done)
        return remaining

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to on-demand, keep using it
        if self._commit_to_od:
            return ClusterType.ON_DEMAND

        # If we're already on on-demand, stick to it
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        remaining = self._get_work_remaining()
        if remaining <= 0.0:
            return ClusterType.NONE

        # Environment parameters
        try:
            t = float(self.env.elapsed_seconds)
        except Exception:
            t = 0.0
        try:
            gap = float(self.env.gap_seconds)
        except Exception:
            gap = 0.0
        try:
            dl = float(self.deadline)
        except Exception:
            dl = t + 1e9
        try:
            overhead = float(self.restart_overhead)
        except Exception:
            overhead = 0.0

        # If even switching to on-demand now cannot meet the deadline, choose OD anyway
        if t + overhead + remaining > dl:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Latest safe time to start on-demand
        fallback_time = dl - (remaining + overhead + gap)

        # If we are past fallback time, commit to on-demand
        if t >= fallback_time:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # If spot not available
        if not has_spot:
            # If waiting one more step would push us past fallback time, start OD now
            if t + gap >= fallback_time:
                self._commit_to_od = True
                return ClusterType.ON_DEMAND
            # Otherwise, wait for cheaper spot
            return ClusterType.NONE

        # Spot is available: decide whether to use it or commit to OD if too close to fallback
        time_until_fallback = fallback_time - t
        if time_until_fallback <= max(gap, overhead * 0.5):
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
