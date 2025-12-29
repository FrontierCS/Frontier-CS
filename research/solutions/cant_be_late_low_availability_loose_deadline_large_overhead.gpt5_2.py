import math
from typing import Any

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:  # Fallbacks for non-evaluation environments
    from enum import Enum

    class ClusterType(Enum):
        SPOT = 1
        ON_DEMAND = 2
        NONE = 3

    class Strategy:
        NAME = "base_strategy"

        def __init__(self, args: Any = None):
            self.env = type(
                "Env",
                (),
                {"elapsed_seconds": 0.0, "gap_seconds": 60.0, "cluster_type": ClusterType.NONE},
            )()
            self.task_duration = 0.0
            self.task_done_time = []
            self.deadline = 0.0
            self.restart_overhead = 0.0

        def solve(self, spec_path: str) -> "Strategy":
            return self


class Solution(Strategy):
    NAME = "cant_be_late_guard_v2"

    def solve(self, spec_path: str) -> "Solution":
        # Initialization of internal state
        self._committed_to_od = False
        self._initialized = True
        return self

    def _remaining_work(self) -> float:
        done = 0.0
        try:
            done = float(sum(self.task_done_time))
        except Exception:
            for seg in self.task_done_time:
                try:
                    done += float(seg)
                except Exception:
                    try:
                        if isinstance(seg, (list, tuple)) and len(seg) >= 2:
                            done += float(seg[1]) - float(seg[0])
                    except Exception:
                        continue
        remaining = float(self.task_duration) - done
        return max(0.0, remaining)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Ensure internal flags exist even if solve() wasn't called
        if not hasattr(self, "_committed_to_od"):
            self._committed_to_od = False

        # If already committed, stay on on-demand until completion
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Compute remaining work and time metrics
        remaining_work = self._remaining_work()
        if remaining_work <= 0.0:
            return ClusterType.NONE

        t = float(self.env.elapsed_seconds)
        gap = float(self.env.gap_seconds)
        deadline = float(self.deadline)
        overhead = float(self.restart_overhead)

        # Latest safe time to start OD (accounting for one restart overhead)
        latest_safe_start = deadline - (remaining_work + overhead)

        # Small safety fudge to avoid edge rounding issues
        fudge = max(1e-6, 1e-3 * gap)

        # Decide: can we safely wait one more step (using SPOT or NONE) and still finish?
        can_wait_one_step = (t + gap + fudge) <= latest_safe_start

        if can_wait_one_step:
            # Prefer Spot if available; otherwise wait (NONE)
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE
        else:
            # Must commit to OD now to meet deadline (or minimize lateness)
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)