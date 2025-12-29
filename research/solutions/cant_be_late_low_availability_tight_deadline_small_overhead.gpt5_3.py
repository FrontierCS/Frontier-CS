import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args
        self._committed_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _progress_done_seconds(self) -> float:
        total = 0.0
        iterable = getattr(self, "task_done_time", []) or []
        for seg in iterable:
            try:
                if isinstance(seg, (list, tuple)):
                    if len(seg) >= 2:
                        total += float(seg[1]) - float(seg[0])
                    elif len(seg) == 1:
                        total += float(seg[0])
                else:
                    total += float(seg)
            except Exception:
                continue
        return max(total, 0.0)

    def _remaining_work_seconds(self) -> float:
        try:
            task_duration = float(self.task_duration)
        except Exception:
            task_duration = 0.0
        done = self._progress_done_seconds()
        rem = task_duration - done
        return rem if rem > 0 else 0.0

    def _latest_start_time_for_od(self, od_overhead: float) -> float:
        try:
            deadline = float(self.deadline)
        except Exception:
            deadline = float("inf")
        rem = self._remaining_work_seconds()
        return deadline - (rem + float(od_overhead))

    def _compute_margins(self):
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        ro = float(getattr(self, "restart_overhead", 180.0) or 180.0)
        margin_switch = max(2.0 * gap, ro + gap, 300.0)
        wait_margin = margin_switch + max(2.0 * gap, 0.5 * ro) + 300.0
        rem = self._remaining_work_seconds()
        total = float(getattr(self, "task_duration", rem) or rem)
        frac = 0.0 if total <= 0 else rem / total
        scale = 0.5 + 0.5 * frac
        margin_switch *= scale
        wait_margin *= scale
        return margin_switch, wait_margin

    def _should_commit_to_od(self, has_spot: bool) -> bool:
        if self._committed_to_od:
            return True
        now = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        ro = float(getattr(self, "restart_overhead", 180.0) or 180.0)
        margin_switch, wait_margin = self._compute_margins()
        current_cluster = getattr(self.env, "cluster_type", None)
        od_overhead_future = 0.0 if current_cluster == ClusterType.ON_DEMAND else ro
        t_latest = self._latest_start_time_for_od(od_overhead_future)
        slack = t_latest - now
        if slack <= margin_switch:
            return True
        if not has_spot and slack <= wait_margin:
            return True
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self._remaining_work_seconds() <= 0:
            self._committed_to_od = False
            return ClusterType.NONE

        if self._should_commit_to_od(has_spot):
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        now = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        ro = float(getattr(self, "restart_overhead", 180.0) or 180.0)
        _, wait_margin = self._compute_margins()
        t_latest = self._latest_start_time_for_od(ro)
        slack = t_latest - now
        if slack > wait_margin:
            return ClusterType.NONE
        self._committed_to_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)