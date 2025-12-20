from typing import Any, List, Tuple, Dict
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self._committed_on_demand: bool = False
        self._last_decision: ClusterType = ClusterType.NONE

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _sum_done_seconds(self) -> float:
        total = 0.0
        segments = getattr(self, "task_done_time", None)
        if segments is None:
            return 0.0
        if isinstance(segments, (int, float)):
            try:
                return float(segments)
            except Exception:
                return 0.0
        if isinstance(segments, list):
            for seg in segments:
                try:
                    if isinstance(seg, (list, tuple)) and len(seg) >= 2:
                        s = float(seg[0])
                        e = float(seg[1])
                        total += max(0.0, e - s)
                    elif isinstance(seg, dict):
                        s = None
                        e = None
                        if "start" in seg or "end" in seg:
                            s = seg.get("start", None)
                            e = seg.get("end", None)
                        elif "s" in seg or "e" in seg:
                            s = seg.get("s", None)
                            e = seg.get("e", None)
                        elif "begin" in seg or "finish" in seg:
                            s = seg.get("begin", None)
                            e = seg.get("finish", None)
                        elif "t0" in seg or "t1" in seg:
                            s = seg.get("t0", None)
                            e = seg.get("t1", None)
                        if s is not None and e is not None:
                            total += max(0.0, float(e) - float(s))
                        elif "duration" in seg:
                            total += max(0.0, float(seg["duration"]))
                    else:
                        total += max(0.0, float(seg))
                except Exception:
                    continue
        else:
            try:
                total = float(segments)
            except Exception:
                total = 0.0
        return max(0.0, total)

    def _remaining_work_seconds(self) -> float:
        try:
            total_needed = float(self.task_duration)
        except Exception:
            total_needed = 0.0
        done = self._sum_done_seconds()
        remain = max(0.0, total_needed - done)
        return remain

    def _commit_check(self, remaining_work: float) -> bool:
        # Time left until deadline
        try:
            now = float(self.env.elapsed_seconds)
            deadline = float(self.deadline)
            g = float(self.env.gap_seconds)
        except Exception:
            return False
        time_left = max(0.0, deadline - now)

        # Overhead is in seconds
        try:
            overhead = float(self.restart_overhead)
        except Exception:
            overhead = 0.0

        # Safety margin to account for discretization and scheduling jitter
        # Aim to start OD slightly earlier than the absolute last moment.
        margin = max(2.0 * g, 2.0 * overhead)

        # Latest start time criterion:
        # If we have time_left <= remaining_work + overhead + margin, we should commit to OD.
        need_time_with_overhead = remaining_work + overhead + margin
        return time_left <= need_time_with_overhead

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we were already on On-Demand, keep committed to avoid risk of switching back to Spot.
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._committed_on_demand = True

        remaining_work = self._remaining_work_seconds()

        # If work is finished, do nothing.
        if remaining_work <= 0:
            self._last_decision = ClusterType.NONE
            return ClusterType.NONE

        # Decide if we must commit to On-Demand to guarantee deadline.
        if not self._committed_on_demand and self._commit_check(remaining_work):
            self._committed_on_demand = True

        if self._committed_on_demand:
            self._last_decision = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND

        # Prefer Spot when available
        if has_spot:
            self._last_decision = ClusterType.SPOT
            return ClusterType.SPOT

        # Spot not available and not yet time-critical: wait to save cost
        self._last_decision = ClusterType.NONE
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
