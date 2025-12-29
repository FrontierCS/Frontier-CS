import argparse
from typing import Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_guard_threshold_v1"

    def __init__(self, args: Optional[argparse.Namespace] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self._commit_od = False
        self._od_commit_time = None
        self._consec_outage_steps = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work_seconds(self) -> float:
        total = float(getattr(self, "task_duration", 0.0) or 0.0)
        done_list = getattr(self, "task_done_time", None)
        if not done_list:
            return max(total, 0.0)
        try:
            progress = float(sum(done_list))
        except Exception:
            try:
                progress = float(sum(float(x) for x in done_list))
            except Exception:
                progress = 0.0
        progress = max(min(progress, total), 0.0)
        return max(total - progress, 0.0)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if has_spot:
            self._consec_outage_steps = 0
        else:
            self._consec_outage_steps += 1

        if self._commit_od:
            return ClusterType.ON_DEMAND

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        remaining = self._remaining_work_seconds()
        time_left = max(deadline - elapsed, 0.0)

        # Safety margin: restart overhead + discretization buffer
        # Slightly conservative to guard against rounding/overhead alignment.
        fudge_seconds = 2.0 * gap + min(180.0, gap)  # 2 steps + up to 3 minutes
        safety = restart_overhead + fudge_seconds

        # Commit to OD if cutting it close
        if time_left <= remaining + safety + 1e-6:
            self._commit_od = True
            self._od_commit_time = elapsed
            return ClusterType.ON_DEMAND

        # Early commit if prolonged outage and we're approaching threshold
        if not has_spot:
            early_buffer = 3.0 * gap + 0.5 * restart_overhead
            outage_threshold_steps = max(int(1800.0 / max(gap, 1.0)), 1)  # ~30 minutes
            if self._consec_outage_steps >= outage_threshold_steps:
                if time_left <= remaining + safety + early_buffer:
                    self._commit_od = True
                    self._od_commit_time = elapsed
                    return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)