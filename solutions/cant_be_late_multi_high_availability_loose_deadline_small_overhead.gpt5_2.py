import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cbl_multi_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Internal state
        self._initialized = False
        self._od_lock = False  # Once ON_DEMAND is chosen to guarantee deadline, keep it.
        self._work_done_sum = 0.0
        self._prev_done_len = 0
        self._num_regions = None
        self._rr_next_region = None  # for round-robin region switching when spot unavailable

        return self

    def _init_if_needed(self):
        if not self._initialized:
            try:
                self._num_regions = self.env.get_num_regions()
            except Exception:
                self._num_regions = 1
            cur = 0
            try:
                cur = self.env.get_current_region()
            except Exception:
                cur = 0
            self._rr_next_region = (cur + 1) % max(1, self._num_regions)
            self._initialized = True

    def _update_work_done_sum(self):
        n = len(self.task_done_time)
        if n > self._prev_done_len:
            # Only sum the newly added segments to avoid O(n) each step
            add = 0.0
            for i in range(self._prev_done_len, n):
                add += self.task_done_time[i]
            self._work_done_sum += add
            self._prev_done_len = n

    def _remaining_work(self) -> float:
        self._update_work_done_sum()
        rem = self.task_duration - self._work_done_sum
        if rem < 0.0:
            rem = 0.0
        return rem

    def _need_on_demand_now(self) -> bool:
        # Decide if we must switch to ON_DEMAND now to finish by deadline
        now = self.env.elapsed_seconds
        available_time = self.deadline - now
        if available_time <= 0:
            return True
        remaining_work = self._remaining_work()
        if remaining_work <= 0:
            return False
        # If we start ON_DEMAND now, we will pay a restart overhead before accruing work
        # Use a tiny epsilon to handle float inaccuracies.
        epsilon = 1e-9
        return (self.restart_overhead + remaining_work) >= (available_time - epsilon)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_if_needed()

        # If already chose ON_DEMAND to guarantee finish, keep using it
        if self._od_lock:
            return ClusterType.ON_DEMAND

        # If task is done, don't run more
        if self._remaining_work() <= 0.0:
            return ClusterType.NONE

        # If we must run ON_DEMAND now to guarantee deadline
        if self._need_on_demand_now():
            self._od_lock = True
            return ClusterType.ON_DEMAND

        # Prefer SPOT whenever available
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable in current region: if there are multiple regions, switch to another region
        if self._num_regions and self._num_regions > 1:
            cur_region = self.env.get_current_region()
            next_region = (cur_region + 1) % self._num_regions
            # prepare for next step; we still cannot use SPOT this step due to has_spot==False
            if next_region != cur_region:
                self.env.switch_region(next_region)
                self._rr_next_region = (next_region + 1) % self._num_regions

        # Wait this step (cost-free) and try again next step
        return ClusterType.NONE
