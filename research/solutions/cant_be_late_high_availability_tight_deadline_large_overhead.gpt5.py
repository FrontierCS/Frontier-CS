import math
from typing import Any

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:  # Fallback stubs for non-evaluation environments
    from enum import Enum

    class ClusterType(Enum):
        SPOT = 1
        ON_DEMAND = 2
        NONE = 3

    class _DummyEnv:
        elapsed_seconds = 0.0
        gap_seconds = 60.0
        cluster_type = ClusterType.NONE

    class Strategy:
        def __init__(self, args=None):
            self.env = _DummyEnv()
            self.task_duration = 0.0
            self.task_done_time = 0.0
            self.deadline = 0.0
            self.restart_overhead = 0.0

        def solve(self, spec_path: str):
            return self


class Solution(Strategy):
    NAME = "lazy_commit_v2"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self._committed_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _compute_done_time(self) -> float:
        tdt = getattr(self, "task_done_time", 0.0)
        if isinstance(tdt, (list, tuple)):
            total = 0.0
            for v in tdt:
                try:
                    total += float(v)
                except Exception:
                    try:
                        # If segment represented as (start, end)
                        if isinstance(v, (list, tuple)) and len(v) >= 2:
                            total += float(v[1]) - float(v[0])
                    except Exception:
                        continue
            return max(total, 0.0)
        try:
            return max(float(tdt), 0.0)
        except Exception:
            return 0.0

    def _remaining_work(self) -> float:
        done = self._compute_done_time()
        return max(float(self.task_duration) - done, 0.0)

    def _should_commit_to_od(self, remaining: float) -> bool:
        t = float(getattr(self.env, "elapsed_seconds", 0.0))
        deadline = float(self.deadline)
        slack = max(deadline - t, 0.0)
        gap = max(float(getattr(self.env, "gap_seconds", 0.0)), 0.0)
        oh = float(self.restart_overhead)

        # Margin accounts for discrete step size and potential scheduling overheads
        # Using 2 gaps and a 60-second cushion
        margin = max(2.0 * gap, 60.0)
        required_if_commit_later = remaining + oh + margin
        return slack <= required_if_commit_later

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining = self._remaining_work()
        if remaining <= 0.0:
            self._committed_to_od = True
            return ClusterType.NONE

        if not self._committed_to_od and self._should_commit_to_od(remaining):
            self._committed_to_od = True

        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)