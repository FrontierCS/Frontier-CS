import sys
from typing import Any

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:  # Fallback stubs for non-eval environments
    from enum import Enum

    class ClusterType(Enum):
        SPOT = 1
        ON_DEMAND = 2
        NONE = 3

    class Strategy:  # type: ignore
        def __init__(self, *args, **kwargs) -> None:
            pass

        def solve(self, spec_path: str):
            return self


class Solution(Strategy):
    NAME = "lazy_fallback_to_od_v1"

    def __init__(self, args: Any = None) -> None:
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args
        self._committed_to_on_demand = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work(self) -> float:
        total = getattr(self, "task_duration", 0.0) or 0.0
        done_list = getattr(self, "task_done_time", None)
        done = 0.0
        if done_list:
            try:
                done = float(sum(done_list))
            except Exception:
                try:
                    done = float(done_list)  # fallback if provided as scalar
                except Exception:
                    done = 0.0
        return max(total - done, 0.0)

    def _should_commit_to_on_demand(self) -> bool:
        if self._committed_to_on_demand:
            return True

        # Gather environment info safely
        now = getattr(self.env, "elapsed_seconds", 0.0) if hasattr(self, "env") else 0.0
        gap = getattr(self.env, "gap_seconds", 0.0) if hasattr(self, "env") else 0.0
        deadline = getattr(self, "deadline", 0.0) or 0.0
        restart = getattr(self, "restart_overhead", 0.0) or 0.0

        remaining = self._remaining_work()
        slack = deadline - now

        # Safety margin: at least one gap to account for step discretization.
        # This keeps us from switching too late and missing the deadline by a rounding step.
        fudge = max(gap, 0.0)

        # If time remaining (slack) is less than or equal to the time needed to complete the job
        # on on-demand (remaining work + one restart overhead) plus a small fudge, commit to OD.
        need_on_demand = remaining + restart + fudge
        return slack <= need_on_demand

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Once on on-demand, never switch back (avoid overhead and risk).
        if self._committed_to_on_demand or self._should_commit_to_on_demand():
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Prefer spot when available until we must commit to on-demand.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable; wait if we still have sufficient buffer before needing OD.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
