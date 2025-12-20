from typing import List, Union, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_hedged_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self._commit_to_od = False
        self._commit_time = None
        self._last_reset_elapsed = -1.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _reset_episode_if_needed(self):
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        # New episode if elapsed resets to 0 or goes backward
        if elapsed == 0.0 or (self._last_reset_elapsed > elapsed and self._last_reset_elapsed >= 0):
            self._commit_to_od = False
            self._commit_time = None
        self._last_reset_elapsed = elapsed

    def _remaining_work_seconds(self) -> float:
        total = float(getattr(self, "task_duration", 0.0) or 0.0)
        done = 0.0
        segs: List[Union[float, int, Tuple[float, float]]] = getattr(self, "task_done_time", []) or []
        for seg in segs:
            if isinstance(seg, (int, float)):
                val = float(seg)
                if val > 0:
                    done += val
            elif isinstance(seg, (list, tuple)) and len(seg) >= 2:
                a, b = seg[0], seg[1]
                if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    d = float(b) - float(a)
                    if d > 0:
                        done += d
        remain = total - done
        if remain < 0:
            remain = 0.0
        return remain

    def _safety_margin_seconds(self) -> float:
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        # Conservative buffer for discretization and overhead handling
        return 2.0 * gap + 60.0

    def _should_commit_to_od(self) -> bool:
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        time_left = deadline - elapsed
        if time_left <= 0:
            return True
        remain = self._remaining_work_seconds()
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        safety = self._safety_margin_seconds()
        need_time = remain + restart_overhead + safety
        return time_left <= need_time

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._reset_episode_if_needed()

        remain = self._remaining_work_seconds()
        if remain <= 0:
            return ClusterType.NONE

        if not self._commit_to_od and self._should_commit_to_od():
            self._commit_to_od = True
            self._commit_time = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)

        if self._commit_to_od:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
