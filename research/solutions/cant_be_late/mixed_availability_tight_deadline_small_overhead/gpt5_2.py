from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "safety_fallback_wait_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self._fallback_active = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work(self) -> float:
        try:
            done = float(sum(self.task_done_time))
        except Exception:
            done = 0.0
            for seg in self.task_done_time or []:
                try:
                    done += float(seg)
                except Exception:
                    try:
                        done += float(seg[1]) - float(seg[0])
                    except Exception:
                        pass
        remaining = self.task_duration - done
        if remaining < 0.0:
            remaining = 0.0
        return remaining

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we've already committed to on-demand fallback, keep it to avoid extra overhead/risk
        if self._fallback_active:
            return ClusterType.ON_DEMAND

        # Compute remaining work and slack
        remaining = self._remaining_work()
        if remaining <= 0.0:
            return ClusterType.NONE

        slack = self.deadline - self.env.elapsed_seconds
        gap = max(float(self.env.gap_seconds), 0.0)
        # Safety buffer to account for discretization and timing uncertainties
        safety_buffer = max(0.5 * gap, 1.0)
        # Use worst-case overhead when switching to OD
        od_overhead = float(self.restart_overhead)

        # Determine if we must switch to On-Demand now to guarantee finish
        must_switch_to_od_now = slack <= (remaining + od_overhead + safety_buffer)

        # Decision rules:
        # 1) If we must switch to OD now, do it and lock in OD until completion.
        if must_switch_to_od_now:
            self._fallback_active = True
            return ClusterType.ON_DEMAND

        # 2) If spot is available and we are safe, use spot.
        if has_spot:
            return ClusterType.SPOT

        # 3) Spot not available: can we afford to wait this step?
        # Safe to wait if after one gap of waiting we still have enough time for OD completion.
        can_wait = (slack - gap) > (remaining + od_overhead + safety_buffer)
        if can_wait:
            return ClusterType.NONE

        # Otherwise, switch to OD now and lock it
        self._fallback_active = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)