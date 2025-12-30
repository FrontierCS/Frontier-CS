from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "just_in_time_od_cbla"

    def __init__(self, args=None):
        super().__init__(args)
        self._commit_od = False
        self._sum_done_cache = 0.0
        self._sum_done_cache_len = -1

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work(self) -> float:
        lst = getattr(self, "task_done_time", None)
        if not lst:
            return max(self.task_duration, 0.0)
        n = len(lst)
        if n != self._sum_done_cache_len:
            self._sum_done_cache = sum(lst)
            self._sum_done_cache_len = n
        done = self._sum_done_cache
        rem = self.task_duration - done
        return rem if rem > 0.0 else 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to OD, stay on OD to avoid overhead and guarantee finish.
        if self._commit_od:
            return ClusterType.ON_DEMAND

        # Compute remaining work and timing
        remaining_work = self._remaining_work()
        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        ttd = self.deadline - elapsed  # time to deadline
        gap = self.env.gap_seconds

        # If we haven't committed to OD yet, we must budget one restart overhead when switching to OD.
        overhead = self.restart_overhead

        required_time_if_switch_to_od_now = remaining_work + overhead

        # Safety checks and decisions
        # If even switching to OD now can't finish, still choose OD (best effort).
        if ttd < required_time_if_switch_to_od_now:
            self._commit_od = True
            return ClusterType.ON_DEMAND

        # Prefer SPOT when available (cost-efficient) as long as fallback remains feasible.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: decide to wait or commit to OD.
        # Safe to wait one step if after waiting we can still finish with OD (including overhead).
        if (ttd - gap) >= required_time_if_switch_to_od_now:
            return ClusterType.NONE

        # Otherwise, must switch to OD now to guarantee finish.
        self._commit_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)