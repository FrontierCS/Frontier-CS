from typing import Any, Optional, List
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "barrier_wait_spot_safe"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self._commit_to_od: bool = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _get_progress_seconds(self) -> float:
        # Robustly compute total progress from available attributes
        # Prefer a direct attribute if present; otherwise sum segments
        val = getattr(self, "task_done_seconds", None)
        if isinstance(val, (int, float)):
            return float(val)
        # Fallback to summing segments
        segs = getattr(self, "task_done_time", None)
        if isinstance(segs, (list, tuple)):
            try:
                return float(sum(segs))
            except Exception:
                return 0.0
        try:
            return float(segs) if segs is not None else 0.0
        except Exception:
            return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to on-demand, keep it to avoid churn and ensure completion
        if self._commit_to_od:
            return ClusterType.ON_DEMAND

        # Extract environment parameters
        now = float(getattr(self.env, "elapsed_seconds", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 60.0))
        deadline = float(getattr(self, "deadline", now))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))
        task_duration = float(getattr(self, "task_duration", 0.0))

        # Compute remaining work and remaining time
        progress = self._get_progress_seconds()
        remaining_work = max(0.0, task_duration - progress)
        time_left = max(0.0, deadline - now)

        # Safety padding to account for discretization and overhead uncertainties
        safety_padding = max(gap * 2.0, restart_overhead * 0.5)

        # Overhead if we start OD now (0 if we are already on OD and continue)
        overhead_if_starting_od = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead

        # Force switching to OD if we are in (or near) the critical zone
        # Condition ensures that starting OD now (considering overhead) can still finish by deadline
        critical_threshold = remaining_work + overhead_if_starting_od + safety_padding
        if time_left <= critical_threshold:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Safe zone: use spot when available, otherwise wait (NONE) to save cost
        if has_spot:
            return ClusterType.SPOT

        # Spot not available; still safe to wait
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
