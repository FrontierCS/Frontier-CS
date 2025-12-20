from typing import Any
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_guard_spot_first"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)  # type: ignore
        except Exception:
            try:
                super().__init__()  # type: ignore
            except Exception:
                pass
        self.args = args
        self.lock_to_on_demand = False
        self._done_sum = 0.0
        self._done_len = 0
        self._fudge_multiplier = 2.0  # multiplier for gap_seconds as safety buffer

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _get_done_seconds(self) -> float:
        try:
            segments = self.task_done_time  # type: ignore[attr-defined]
        except Exception:
            return 0.0
        if not isinstance(segments, list):
            return float(self._done_sum)
        l = len(segments)
        if l > self._done_len:
            add = 0.0
            for v in segments[self._done_len:]:
                try:
                    add += float(v)
                except Exception:
                    continue
            self._done_sum += add
            self._done_len = l
        return float(self._done_sum)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Basic environment values (seconds)
        elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        gap = max(getattr(self.env, "gap_seconds", 0.0), 1.0)
        deadline = getattr(self, "deadline", elapsed + gap)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))
        task_duration = float(getattr(self, "task_duration", 0.0))

        done = self._get_done_seconds()
        remaining = max(0.0, task_duration - done)
        time_left = max(0.0, deadline - elapsed)

        # If already locking to OD, keep using it
        if self.lock_to_on_demand:
            return ClusterType.ON_DEMAND

        # Safety buffer to account for discretization and control delay
        fudge = max(self._fudge_multiplier * gap, restart_overhead)

        # Overhead if switching to OD now
        overhead_if_switch_now = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead

        # If the remaining time is tight, commit to OD to guarantee deadline
        if time_left <= remaining + overhead_if_switch_now + fudge:
            self.lock_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Otherwise, use SPOT if available; else wait
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
