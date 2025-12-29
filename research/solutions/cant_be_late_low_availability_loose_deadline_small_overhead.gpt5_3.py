from typing import Any
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "lazy_od_guard"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args
        self._od_lockin = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work_seconds(self) -> float:
        try:
            total = float(getattr(self, "task_duration", 0.0) or 0.0)
        except Exception:
            total = 0.0
        done_list = getattr(self, "task_done_time", []) or []
        progress = 0.0
        try:
            for seg in done_list:
                try:
                    progress += float(seg)
                except Exception:
                    continue
        except Exception:
            progress = 0.0
        remaining = total - progress
        if remaining < 0.0:
            remaining = 0.0
        return remaining

    def _time_remaining_seconds(self) -> float:
        try:
            elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
            deadline = float(getattr(self, "deadline", 0.0) or 0.0)
            tr = deadline - elapsed
            if tr < 0.0:
                tr = 0.0
            return tr
        except Exception:
            return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to on-demand, keep using it.
        if self._od_lockin:
            return ClusterType.ON_DEMAND

        # Robust defaults
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        remaining_work = self._remaining_work_seconds()
        time_remaining = self._time_remaining_seconds()

        # If no remaining work, do nothing (env should stop soon).
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Determine overhead if we switch/start On-Demand now.
        # If we were already on OD last step, continuing OD doesn't require restart overhead.
        overhead_if_start_od_now = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead

        # Latest-safe-start policy:
        # When time remaining is less than or equal to time needed on OD plus one step buffer,
        # start OD now and lock-in to guarantee completion.
        time_needed_on_demand = remaining_work + overhead_if_start_od_now

        must_start_od = time_remaining <= (time_needed_on_demand + gap)

        if must_start_od:
            self._od_lockin = True
            return ClusterType.ON_DEMAND

        # Otherwise, be opportunistic: use spot when available; else wait.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)