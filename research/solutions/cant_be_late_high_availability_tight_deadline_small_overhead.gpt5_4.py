from typing import Any
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self._commit_on_demand = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _done_seconds(self) -> float:
        done = 0.0
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return 0.0
        try:
            for seg in segments:
                if isinstance(seg, (int, float)):
                    done += float(seg)
                elif isinstance(seg, (list, tuple)) and len(seg) >= 2:
                    try:
                        done += float(seg[1] - seg[0])
                    except Exception:
                        # Fallback if segment is malformed
                        try:
                            done += float(seg[0])
                        except Exception:
                            pass
                elif hasattr(seg, "duration"):
                    try:
                        done += float(seg.duration)
                    except Exception:
                        pass
        except Exception:
            # As a safe fallback, if format is unexpected, don't add anything
            pass
        return done

    def _remaining_seconds(self) -> float:
        return max(0.0, float(self.task_duration) - self._done_seconds())

    def _time_left(self) -> float:
        return float(self.deadline) - float(self.env.elapsed_seconds)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to OD or currently on OD, stick with OD until finished.
        rem = self._remaining_seconds()
        if rem <= 0:
            return ClusterType.NONE

        if self._commit_on_demand or last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        time_left = self._time_left()
        if time_left <= 0:
            return ClusterType.NONE

        gap = float(self.env.gap_seconds)
        oh = float(self.restart_overhead)

        # If Spot is available, decide whether we can safely use it for one more step.
        if has_spot:
            # Compute progress this step on Spot:
            # - If we were on Spot last step and still have Spot now, no restart overhead this step.
            # - Otherwise, we'll pay overhead before making progress on this step.
            if last_cluster_type == ClusterType.SPOT:
                progress_this_step = min(gap, rem)
            else:
                progress_this_step = max(0.0, min(gap, rem) - oh)

            # If we can finish this step on Spot, do it.
            if progress_this_step >= rem:
                return ClusterType.SPOT

            # Otherwise, check if it's safe to spend this step on Spot and still finish by
            # switching to OD afterward (including one OD restart overhead).
            post_rem = rem - progress_this_step
            post_time_left = time_left - gap

            if post_time_left >= post_rem + oh:
                return ClusterType.SPOT
            else:
                # Not safe to wait; commit to On-Demand now.
                self._commit_on_demand = True
                return ClusterType.ON_DEMAND

        # If Spot is not available, decide whether to idle or commit to On-Demand.
        # It's safe to idle one step only if after idling we can still finish by switching to OD.
        post_time_left = time_left - gap
        if post_time_left >= rem + oh:
            return ClusterType.NONE
        else:
            self._commit_on_demand = True
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)