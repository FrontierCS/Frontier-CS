import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "safe_spot_deadline_strategy"

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
        self._locked_on_demand = False
        self._rotation_initialized = False
        return self

    def _remaining_work_seconds(self) -> float:
        return max(0.0, self.task_duration - sum(self.task_done_time))

    def _time_left_seconds(self) -> float:
        return max(0.0, self.deadline - self.env.elapsed_seconds)

    def _od_time_to_finish_if_start_now(self, last_cluster_type: ClusterType) -> float:
        # Time to finish if we run On-Demand starting this step.
        # If we are already on OD and continue, no restart overhead.
        remaining = self._remaining_work_seconds()
        if remaining <= 0:
            return 0.0
        overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead
        return remaining + overhead

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize rotation starting region on first call
        if not self._rotation_initialized:
            self._rotation_initialized = True

        remaining_work = self._remaining_work_seconds()
        if remaining_work <= 0:
            return ClusterType.NONE

        time_left = self._time_left_seconds()
        gap = self.env.gap_seconds
        overhead = self.restart_overhead

        # If already on On-Demand, stay on OD to avoid overhead and guarantee completion.
        if self._locked_on_demand or last_cluster_type == ClusterType.ON_DEMAND:
            self._locked_on_demand = True
            return ClusterType.ON_DEMAND

        # Compute minimal OD time to finish if we start OD now.
        od_time_now = self._od_time_to_finish_if_start_now(last_cluster_type)

        # If we cannot safely finish unless we start OD now, do it.
        if time_left <= od_time_now:
            self._locked_on_demand = True
            return ClusterType.ON_DEMAND

        # Safety policy to try spot:
        # Only try spot if we keep at least one full step slack beyond OD finish time.
        # This ensures that even if we lose this entire step, we can still switch to OD and finish.
        safe_spot_slack = overhead + gap  # overhead to switch to OD later + one lost step
        need_time_for_safe_spot_try = remaining_work + safe_spot_slack

        if has_spot:
            if time_left > need_time_for_safe_spot_try:
                return ClusterType.SPOT
            else:
                self._locked_on_demand = True
                return ClusterType.ON_DEMAND
        else:
            # No spot in current region. If we have extra slack, we can wait and rotate to seek spot.
            # Require an additional gap of slack (total two steps slack) to wait this step.
            extra_wait_steps = 2.0  # total wait allowance beyond OD time (includes the above one lost step)
            wait_threshold = remaining_work + overhead + gap * extra_wait_steps

            if time_left > wait_threshold:
                # Rotate region to explore other availability and wait this step (no cost).
                num_regions = self.env.get_num_regions()
                if num_regions > 1:
                    new_region = (self.env.get_current_region() + 1) % num_regions
                    self.env.switch_region(new_region)
                return ClusterType.NONE
            else:
                self._locked_on_demand = True
                return ClusterType.ON_DEMAND