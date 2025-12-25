from typing import Any
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_v1"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self._commit_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _estimate_done(self) -> float:
        total = 0.0
        try:
            segments = self.task_done_time or []
        except Exception:
            segments = []
        for seg in segments:
            try:
                if isinstance(seg, (list, tuple)) and len(seg) >= 2:
                    total += float(seg[1]) - float(seg[0])
                else:
                    total += float(seg)
            except Exception:
                continue
        if total < 0:
            total = 0.0
        return total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to on-demand, keep using it.
        if self._commit_od:
            return ClusterType.ON_DEMAND

        # Estimate remaining work conservatively.
        done_est = self._estimate_done()
        remaining = max(self.task_duration - done_est, 0.0)

        # If nothing remains, do nothing.
        if remaining <= 0:
            return ClusterType.NONE

        t = float(self.env.elapsed_seconds)
        gap = float(self.env.gap_seconds)
        deadline = float(self.deadline)
        ro = float(self.restart_overhead)

        time_left = max(deadline - t, 0.0)

        # Spare time if we switched to OD immediately (paying restart overhead once).
        spare_time = time_left - (remaining + ro)

        # Safety buffer to account for step discretization and conservative done estimation.
        buffer_time = ro + 2.0 * gap

        # If we are within the buffer, commit to OD now to guarantee finish.
        if spare_time <= buffer_time:
            self._commit_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, pursue cheap options: use SPOT if available; else wait.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)