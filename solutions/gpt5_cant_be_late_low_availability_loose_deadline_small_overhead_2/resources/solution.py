from typing import Any, Iterable, Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_wait"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self._committed_to_od: bool = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _sum_segment(self, seg) -> float:
        if isinstance(seg, (int, float)):
            return float(seg)
        if isinstance(seg, dict):
            if "duration" in seg:
                return float(seg["duration"])
            if "dur" in seg:
                return float(seg["dur"])
            if "seconds" in seg:
                return float(seg["seconds"])
            if "end" in seg and "start" in seg:
                try:
                    return float(seg["end"]) - float(seg["start"])
                except Exception:
                    return 0.0
        if hasattr(seg, "duration"):
            try:
                return float(seg.duration)
            except Exception:
                return 0.0
        if isinstance(seg, (list, tuple)) and len(seg) >= 2:
            a, b = seg[0], seg[1]
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                return float(b) - float(a)
        return 0.0

    def _done_seconds(self) -> float:
        try:
            arr = self.task_done_time
        except Exception:
            return 0.0
        if arr is None:
            return 0.0
        if isinstance(arr, (int, float)):
            return float(arr)
        if isinstance(arr, Iterable):
            total = 0.0
            for seg in arr:
                total += self._sum_segment(seg)
            return max(total, 0.0)
        return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we've already committed to OD, never switch back
        if self._committed_to_od or last_cluster_type == ClusterType.ON_DEMAND:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        done = self._done_seconds()
        remaining = max(self.task_duration - done, 0.0)

        # If done (should be handled by env), choose NONE
        if remaining <= 0.0:
            return ClusterType.NONE

        t = float(self.env.elapsed_seconds)
        gap = float(self.env.gap_seconds)
        deadline = float(self.deadline)
        restart = float(self.restart_overhead)

        # Small conservative pad to account for discretization/rounding
        safety_pad = 0.5 * min(gap, restart)

        # Check if it's safe to postpone OD commitment by one more step even with zero progress in this step
        # Worst-case for this step: no progress; next step we start OD and pay restart overhead.
        safe_to_wait = (t + gap + restart + remaining) <= (deadline - safety_pad)

        if not safe_to_wait:
            # If we're currently on SPOT and it is available, we can safely use SPOT for this step
            # if after getting gap seconds of progress (no new overhead), we can still start OD next step.
            if has_spot and last_cluster_type == ClusterType.SPOT:
                rem_after = max(0.0, remaining - gap)
                if (t + gap + restart + rem_after) <= (deadline - safety_pad):
                    return ClusterType.SPOT
            # Otherwise, must commit to OD now to guarantee deadline
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Safe to wait one more step:
        if has_spot:
            return ClusterType.SPOT
        else:
            # No spot this step; wait to save cost since we still have slack
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
