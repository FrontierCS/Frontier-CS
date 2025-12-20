from typing import Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_guard_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self.args = args
        self.force_on_demand: bool = False
        self._sum_cache_len: int = -1
        self._sum_cache_val: float = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _sum_task_done(self) -> float:
        tdt = getattr(self, "task_done_time", [])
        try:
            n = len(tdt)
        except Exception:
            # Fallback in case task_done_time isn't sized normally
            try:
                return float(sum(tdt))
            except Exception:
                return 0.0
        if n != self._sum_cache_len:
            try:
                self._sum_cache_val = float(sum(tdt))
            except Exception:
                self._sum_cache_val = 0.0
            self._sum_cache_len = n
        return self._sum_cache_val

    def _fudge_seconds(self) -> float:
        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
        extra = 0.0
        if self.args is not None and hasattr(self.args, "extra_fudge_seconds") and self.args.extra_fudge_seconds is not None:
            try:
                extra = float(self.args.extra_fudge_seconds)
            except Exception:
                extra = 0.0
        return max(gap, 0.0) + max(extra, 0.0)

    def _remaining_work_seconds(self) -> float:
        total = float(getattr(self, "task_duration", 0.0) or 0.0)
        done = self._sum_task_done()
        rem = total - done
        if rem < 0.0:
            return 0.0
        return rem

    def _time_left_seconds(self) -> float:
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        tl = deadline - elapsed
        if tl < 0.0:
            return 0.0
        return tl

    def _od_needed_now(self, last_cluster_type: ClusterType) -> bool:
        remaining = self._remaining_work_seconds()
        time_left = self._time_left_seconds()
        fudge = self._fudge_seconds()
        overhead_if_switch = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_if_switch = 0.0
        threshold = remaining + overhead_if_switch + fudge
        return time_left <= threshold

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to on-demand, keep it to avoid overhead/thrashing.
        if self.force_on_demand:
            return ClusterType.ON_DEMAND

        # Decide if we need to commit to on-demand now to guarantee finishing by deadline.
        if self._od_needed_now(last_cluster_type):
            self.force_on_demand = True
            return ClusterType.ON_DEMAND

        # Otherwise, prefer spot when available; else wait to save cost.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        # Allow optional tuning via CLI without breaking unknown args
        parser.add_argument("--extra_fudge_seconds", type=float, default=0.0)
        args, _ = parser.parse_known_args()
        return cls(args)
