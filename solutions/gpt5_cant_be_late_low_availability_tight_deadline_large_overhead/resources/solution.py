from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_fallback_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self._ever_committed_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _sum_done(self):
        try:
            if not self.task_done_time:
                return 0.0
            return float(sum(self.task_done_time))
        except Exception:
            return 0.0

    def _remaining_work(self):
        remaining = self.task_duration - self._sum_done()
        if remaining < 0:
            remaining = 0.0
        return remaining

    def _compute_buffer(self, step_s: float, overhead_s: float, remaining_s: float, time_left_s: float) -> float:
        # Base buffer: robust against immediate preemption and step discretization
        base = max(overhead_s * 1.5, step_s * 5.0)
        # Dynamic buffer: small fraction of remaining work (capped)
        dynamic = min(1800.0, 0.02 * max(remaining_s, 0.0))
        # Cap overall buffer to 1 hour
        return min(3600.0, base + dynamic)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Sticky ON_DEMAND: once running on OD, never switch back (avoid extra overhead and risk)
        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        # Compute current state
        elapsed = float(self.env.elapsed_seconds)
        step_s = max(1.0, float(self.env.gap_seconds))
        remaining_s = self._remaining_work()
        if remaining_s <= 0.0:
            return ClusterType.NONE
        time_left_s = max(0.0, float(self.deadline) - elapsed)
        overhead_s = float(self.restart_overhead)

        # Commit threshold: if we must ensure completion, switch to OD now
        buffer_s = self._compute_buffer(step_s, overhead_s, remaining_s, time_left_s)
        must_commit = time_left_s <= (remaining_s + overhead_s + buffer_s)

        if must_commit:
            return ClusterType.ON_DEMAND

        # Prefer Spot when available, otherwise decide to wait or commit to OD
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: wait if we still have slack for one more step, else commit to OD
        if (time_left_s - step_s) > (remaining_s + overhead_s + buffer_s):
            return ClusterType.NONE

        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
