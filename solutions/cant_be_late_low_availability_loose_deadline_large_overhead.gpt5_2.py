from typing import Any, Iterable

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_safe_spot_first"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args
        self._committed_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _sum_task_done(self) -> float:
        td = getattr(self, "task_done_time", 0.0)
        try:
            if isinstance(td, (int, float)):
                return float(td)
            s = 0.0
            if isinstance(td, dict):
                # In case it's a mapping of segments -> durations
                for v in td.values():
                    if isinstance(v, (int, float)):
                        s += float(v)
                return s
            # Assume iterable of numbers
            for x in td:  # type: ignore
                if isinstance(x, (int, float)):
                    s += float(x)
            return s
        except Exception:
            # Fallback if structure is unknown
            return 0.0

    def _remaining_work(self) -> float:
        done = self._sum_task_done()
        rem = float(getattr(self, "task_duration", 0.0)) - done
        return max(0.0, rem)

    def _time_remaining(self) -> float:
        deadline = float(getattr(self, "deadline", 0.0))
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        return max(0.0, deadline - elapsed)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Once we run on-demand at any point, latch to on-demand forever
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._committed_od = True
        if self._committed_od:
            return ClusterType.ON_DEMAND

        # Compute remaining work and time
        work_rem = self._remaining_work()
        if work_rem <= 0.0:
            return ClusterType.NONE

        time_rem = self._time_remaining()
        gap = float(getattr(self.env, "gap_seconds", 0.0))
        restart = float(getattr(self, "restart_overhead", 0.0))

        # Overhead if we choose to start OD now
        overhead_now = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart

        # If we must switch to OD now to guarantee deadline, do it and latch
        if time_rem <= work_rem + overhead_now + 1e-9:
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # Safe-to-risk logic:
        # If we spend one step not using guaranteed OD (i.e., SPOT if available or NONE if not),
        # to still guarantee finishing with OD from the next step regardless of progress this step,
        # we need:
        # time_rem >= work_rem + restart (to start OD next step) + gap (time spent this step even if zero progress)
        safe_margin = gap
        need_if_delay_one_step_then_OD = work_rem + restart + safe_margin

        if has_spot:
            if time_rem >= need_if_delay_one_step_then_OD:
                return ClusterType.SPOT
            else:
                self._committed_od = True
                return ClusterType.ON_DEMAND
        else:
            if time_rem >= need_if_delay_one_step_then_OD:
                return ClusterType.NONE
            else:
                self._committed_od = True
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
