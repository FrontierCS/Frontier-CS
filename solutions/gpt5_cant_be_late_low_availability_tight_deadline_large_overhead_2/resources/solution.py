from typing import Any
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "slack_guard_commit_v2"

    def __init__(self, args: Any = None):
        self.args = args
        self.lock_on_demand = False

    def solve(self, spec_path: str) -> "Solution":
        self.lock_on_demand = False
        return self

    def _completed_work(self) -> float:
        # task_done_time is a list of completed work segments (in seconds).
        # Sum to get total progress; clamp to [0, task_duration].
        try:
            done = float(sum(self.task_done_time)) if self.task_done_time else 0.0
        except Exception:
            done = 0.0
        if done < 0:
            done = 0.0
        if done > self.task_duration:
            return self.task_duration
        return done

    def _should_commit_to_on_demand(self) -> bool:
        # Compute whether it's time to switch (and stick) to on-demand to guarantee finishing.
        # We commit when time_left <= remaining_work + overhead_to_switch + safety_margin.
        time_left = max(0.0, self.deadline - self.env.elapsed_seconds)
        remaining_work = max(0.0, self.task_duration - self._completed_work())

        if remaining_work <= 0.0:
            return False

        # Overhead to consider if we are not already on ON_DEMAND.
        overhead_if_switch = 0.0 if self.env.cluster_type == ClusterType.ON_DEMAND else float(self.restart_overhead)

        # Safety margin for step discretization and minor timing uncertainties.
        gap = float(self.env.gap_seconds)
        safety_margin = max(60.0, 2.0 * gap)

        required_time_if_commit_now = remaining_work + overhead_if_switch + safety_margin
        return time_left <= required_time_if_commit_now

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to on-demand, never switch back.
        if self.lock_on_demand:
            return ClusterType.ON_DEMAND

        # If task already finished (shouldn't be called, but safe-guard).
        remaining_work = max(0.0, self.task_duration - self._completed_work())
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Decide if it's time to commit to on-demand to guarantee deadline.
        if self._should_commit_to_on_demand():
            self.lock_on_demand = True
            return ClusterType.ON_DEMAND

        # Otherwise, leverage spot when available; pause if not available to save cost.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
