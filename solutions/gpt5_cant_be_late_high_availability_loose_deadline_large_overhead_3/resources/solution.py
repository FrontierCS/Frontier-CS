from typing import Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_guard_v2"

    def __init__(self, args: Optional[object] = None):
        super().__init__(args)
        self._commit_to_on_demand = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work(self) -> float:
        done = 0.0
        if getattr(self, "task_done_time", None):
            try:
                done = float(sum(self.task_done_time))
            except Exception:
                done = 0.0
        remaining = float(self.task_duration) - done
        if remaining < 0:
            remaining = 0.0
        return remaining

    def _time_left(self) -> float:
        t_left = float(self.deadline) - float(self.env.elapsed_seconds)
        if t_left < 0:
            t_left = 0.0
        return t_left

    def _safe_slack_threshold(self) -> float:
        # Safety threshold to keep a buffer for one step of potential lost time
        # plus the restart overhead that will be incurred when switching to OD.
        # Using exactly: overhead + one gap buffer.
        return float(self.restart_overhead) + float(self.env.gap_seconds)

    def _must_switch_to_on_demand(self, remaining_work: float, time_left: float) -> bool:
        # If time left is less than or equal to remaining compute plus required overhead buffer,
        # we must run on OD now to guarantee finishing.
        threshold = remaining_work + self._safe_slack_threshold()
        return time_left <= threshold

    def _should_wait_when_no_spot(self, remaining_work: float, time_left: float) -> bool:
        # Decide whether waiting (NONE) for one step is safe while spot is unavailable.
        # Safe if we can still, after waiting one gap and paying a restart overhead,
        # finish on OD: i.e., time_left - gap >= remaining_work + restart_overhead.
        gap = float(self.env.gap_seconds)
        return (time_left - gap) > (remaining_work + float(self.restart_overhead))

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we already committed to OD, stay there
        if self._commit_to_on_demand:
            return ClusterType.ON_DEMAND

        remaining_work = self._remaining_work()
        time_left = self._time_left()

        if remaining_work <= 0.0:
            return ClusterType.NONE

        # If we must switch to OD to guarantee finish, commit now
        if self._must_switch_to_on_demand(remaining_work, time_left):
            self._commit_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Otherwise, prefer Spot when available
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: decide to wait or use OD
        if self._should_wait_when_no_spot(remaining_work, time_left):
            return ClusterType.NONE

        # Not safe to wait any longer; commit to OD
        self._commit_to_on_demand = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
