from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self._od_latched = False
        self._last_task_done_len = 0
        self._cached_done_total = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _sum_done(self):
        # Cache sum(task_done_time) to avoid repeated O(n) sums
        lst = self.task_done_time
        n = len(lst)
        if n != self._last_task_done_len:
            self._cached_done_total = sum(lst)
            self._last_task_done_len = n
        return self._cached_done_total

    def _remaining_work(self):
        remaining = self.task_duration - self._sum_done()
        if remaining < 0:
            return 0.0
        return remaining

    def _must_switch_to_od_now(self, last_cluster_type):
        # If we must switch to OD now to finish by deadline
        remaining_time = self.deadline - self.env.elapsed_seconds
        if remaining_time <= 0:
            return True
        remaining_work = self._remaining_work()
        if remaining_work <= 0:
            return False
        overhead_now = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead
        return remaining_time <= (overhead_now + remaining_work)

    def _safe_to_wait_one_step(self):
        # Check if it's safe to not run OD this step:
        # After one step with no progress, can we still finish with OD (paying one overhead)?
        remaining_time = self.deadline - self.env.elapsed_seconds
        gap = self.env.gap_seconds
        remaining_work = self._remaining_work()
        # If already no time left, not safe
        if remaining_time <= 0:
            return False
        # If we wait one step (no progress), then we need overhead + remaining_work within remaining_time - gap
        # We use strict inequality margin of 1 second to avoid boundary issues
        return (remaining_time - gap) > (self.restart_overhead + remaining_work + 1.0)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If task already completed, do nothing
        if self._remaining_work() <= 0:
            return ClusterType.NONE

        # Once we decide to use OD to secure the deadline, stay on OD until completion
        if self._od_latched:
            return ClusterType.ON_DEMAND

        # If we must switch to OD now to make the deadline, do so and latch
        if self._must_switch_to_od_now(last_cluster_type):
            self._od_latched = True
            return ClusterType.ON_DEMAND

        # If it's not safe to wait one more step (worst case no progress), switch to OD and latch
        if not self._safe_to_wait_one_step():
            self._od_latched = True
            return ClusterType.ON_DEMAND

        # Otherwise, opportunistically use Spot if available; else wait
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
