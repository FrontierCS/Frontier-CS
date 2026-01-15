import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "safe_rotating_guard"

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
        self._committed_od = False
        self._sum_task_done = 0.0
        self._last_task_done_len = 0
        self._initialized = False
        self._eps = 1e-6  # seconds tolerance

        return self

    def _init_if_needed(self):
        if self._initialized:
            return
        # Initialize per-run state that depends on env
        self._num_regions = self.env.get_num_regions()
        self._initialized = True

    def _update_work_done_sum(self):
        # Efficiently update cumulative work done to avoid summing every step
        cur_len = len(self.task_done_time)
        if cur_len > self._last_task_done_len:
            for i in range(self._last_task_done_len, cur_len):
                self._sum_task_done += self.task_done_time[i]
            self._last_task_done_len = cur_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_if_needed()
        self._update_work_done_sum()

        # Basic quantities (seconds)
        gap = float(self.env.gap_seconds)
        time_elapsed = float(self.env.elapsed_seconds)
        time_left = float(self.deadline - time_elapsed)

        remaining_work = max(0.0, float(self.task_duration - self._sum_task_done))

        # If already finished or no time left, do nothing
        if remaining_work <= self._eps or time_left <= self._eps:
            return ClusterType.NONE

        # Once committed, stay on on-demand to guarantee completion
        if self._committed_od:
            return ClusterType.ON_DEMAND

        # Determine if we can afford to spend this whole step not on OD (worst case 0 progress)
        # Safety condition: after spending one full gap doing SPOT/NONE (worst-case no progress),
        # we still must be able to finish with on-demand including one restart overhead.
        # So require: time_left - gap >= remaining_work + restart_overhead
        # Add small epsilon margin to avoid floating issues.
        can_afford_non_od_step = (time_left - gap) >= (remaining_work + self.restart_overhead - self._eps)

        if not can_afford_non_od_step:
            # Must commit to on-demand now to safely finish
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # We can afford a non-OD step this round:
        if has_spot:
            # Prefer spot when available
            return ClusterType.SPOT

        # Spot not available: wait and rotate region to try finding spot next step
        if self._num_regions > 1:
            next_region = (self.env.get_current_region() + 1) % self._num_regions
            self.env.switch_region(next_region)
        return ClusterType.NONE