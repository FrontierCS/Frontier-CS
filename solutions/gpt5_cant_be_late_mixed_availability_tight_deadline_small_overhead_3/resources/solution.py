import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "jit_od_guard"

    def __init__(self, args=None):
        super().__init__(args)
        self.args = args
        self._commit_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _guard_time(self) -> float:
        gap = getattr(self.env, 'gap_seconds', 60.0) or 60.0
        oh = getattr(self, 'restart_overhead', 0.0) or 0.0
        # Guard band to account for startup overhead and control loop granularity
        guard = max(600.0, 4.0 * gap, oh + 2.0 * gap)
        try:
            gb = getattr(self.args, 'guard_band_seconds', None)
            if gb is not None and gb > 0:
                guard = float(gb)
        except Exception:
            pass
        return guard

    def _remaining_work(self) -> float:
        done_list = getattr(self, 'task_done_time', None)
        if not done_list:
            done = 0.0
        else:
            try:
                done = float(sum(done_list))
            except Exception:
                done = 0.0
        total = getattr(self, 'task_duration', 0.0) or 0.0
        remaining = max(0.0, total - done)
        return remaining

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining = self._remaining_work()
        if remaining <= 0.0:
            return ClusterType.NONE

        t_now = self.env.elapsed_seconds
        t_left = max(0.0, self.deadline - t_now)
        gap = self.env.gap_seconds
        guard = self._guard_time()

        on_od_now = (self.env.cluster_type == ClusterType.ON_DEMAND)
        overhead_if_switch_to_od_now = 0.0 if on_od_now else self.restart_overhead
        slack_now = t_left - (remaining + overhead_if_switch_to_od_now)

        if self._commit_to_od:
            return ClusterType.ON_DEMAND

        # If we're approaching deadline buffer, commit to OD
        if slack_now <= guard:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        # Spot not available; evaluate if we can afford to wait a step
        slack_after_wait = (t_left - gap) - (remaining + self.restart_overhead)
        if slack_after_wait <= guard:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        try:
            parser.add_argument("--guard_band_seconds", type=float, default=None)
        except Exception:
            pass
        args, _ = parser.parse_known_args()
        return cls(args)
