import math
from typing import Any, Optional, Iterable

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "safe_spot_then_od_commit_v1"

    def __init__(self, args: Optional[Any] = None):
        self.args = args
        self.committed_to_on_demand = False
        self._last_done_len = -1
        self._cached_done = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _sum_done(self, segments: Optional[Iterable]) -> float:
        if not segments:
            return 0.0
        total = 0.0
        for seg in segments:
            try:
                if isinstance(seg, (int, float)):
                    v = float(seg)
                    if v > 0:
                        total += v
                elif isinstance(seg, (list, tuple)) and len(seg) >= 2:
                    a, b = seg[0], seg[1]
                    af = float(a)
                    bf = float(b)
                    if bf > af:
                        total += (bf - af)
                else:
                    # Fallback: try to cast to float directly
                    v = float(seg)
                    if v > 0:
                        total += v
            except Exception:
                # Ignore malformed segments
                continue
        return total

    def _work_done_seconds(self) -> float:
        segs = getattr(self, "task_done_time", None)
        # Simple cache based on length; conservative if segments mutate in place
        if isinstance(segs, list):
            if len(segs) == self._last_done_len:
                return self._cached_done
            done = self._sum_done(segs)
            self._cached_done = min(done, float(getattr(self, "task_duration", done)))
            self._last_done_len = len(segs)
            return self._cached_done
        # If not list, compute directly
        done = self._sum_done(segs)
        return min(done, float(getattr(self, "task_duration", done)))

    def _remaining_work_seconds(self) -> float:
        total = float(getattr(self, "task_duration", 0.0) or 0.0)
        done = self._work_done_seconds()
        rem = total - done
        if rem < 0:
            return 0.0
        return rem

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Defensive fetches
        now = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        deadline = float(getattr(self, "deadline", now + 1e9) or (now + 1e9))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        # Conservative remaining work calculation
        remaining_work = self._remaining_work_seconds()

        # If nothing remains, do nothing (environment should stop soon)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Safety buffer to account for step discretization and modeling mismatch
        # Choose a small buffer: min(1.5 * gap, 0.3 * overhead)
        # This keeps us slightly conservative without sacrificing too much cost.
        safety_buffer = max(0.0, min(1.5 * gap, 0.3 * restart_overhead))

        time_left = deadline - now
        if time_left <= 0:
            # Already at/past deadline; best effort is OD
            self.committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Determine if we must commit to OD to guarantee deadline.
        # Worst-case assumption from this point forward: no more spot progress.
        # So to finish, we need: overhead (if switching to OD) + remaining_work <= time_left
        overhead_if_switching = 0.0
        if not self.committed_to_on_demand and last_cluster_type != ClusterType.ON_DEMAND:
            overhead_if_switching = restart_overhead

        must_commit_now = (time_left <= (remaining_work + overhead_if_switching + safety_buffer))

        if must_commit_now:
            self.committed_to_on_demand = True

        if self.committed_to_on_demand:
            return ClusterType.ON_DEMAND

        # Opportunistic phase: prefer SPOT when available, otherwise wait (NONE)
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)