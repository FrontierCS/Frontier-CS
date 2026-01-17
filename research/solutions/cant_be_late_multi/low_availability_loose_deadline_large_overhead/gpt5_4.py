import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_lazy_fallback_v2"

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
        self._committed = False
        self._no_spot_count = 0
        gap = self.env.gap_seconds
        # Switch region only if waiting longer than overhead is likely beneficial.
        self._switch_threshold_steps = max(2, int(math.ceil(self.restart_overhead / gap)) + 1)
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Remaining required work in seconds
        remain_work = max(0.0, self.task_duration - sum(self.task_done_time))
        if remain_work <= 0.0:
            return ClusterType.NONE

        now = self.env.elapsed_seconds
        time_left = self.deadline - now
        gap = self.env.gap_seconds

        # Once we switch to On-Demand, stay on it to avoid extra overhead and risk.
        if self._committed or last_cluster_type == ClusterType.ON_DEMAND:
            self._committed = True
            return ClusterType.ON_DEMAND

        overhead_if_od_now = self.restart_overhead
        safety_margin = max(gap, 0.0)

        # If we must commit now to guarantee finishing by deadline
        if time_left <= remain_work + overhead_if_od_now + safety_margin:
            self._committed = True
            self._no_spot_count = 0
            return ClusterType.ON_DEMAND

        # Prefer SPOT when available and not yet committed
        if has_spot:
            self._no_spot_count = 0
            return ClusterType.SPOT

        # Spot not available: decide to idle, switch region, or commit to OD if cannot idle
        # Guard: can we afford idling one full step and still finish if we switch to OD next step?
        if time_left - gap <= remain_work + self.restart_overhead + safety_margin:
            self._committed = True
            self._no_spot_count = 0
            return ClusterType.ON_DEMAND

        # We can afford to wait at least one step
        self._no_spot_count += 1

        # Consider switching regions if prolonged unavailability and multiple regions exist
        num_regions = self.env.get_num_regions() if hasattr(self.env, "get_num_regions") else 1
        should_switch = False
        if num_regions > 1 and self._no_spot_count >= self._switch_threshold_steps:
            # Avoid switching too close to commit; ensure extra slack for switch + potential later OD commit
            if time_left - gap > remain_work + self.restart_overhead + safety_margin + self.restart_overhead:
                should_switch = True

        if should_switch:
            new_region = (self.env.get_current_region() + 1) % num_regions
            if new_region != self.env.get_current_region():
                self.env.switch_region(new_region)
            self._no_spot_count = 0
            return ClusterType.NONE

        # Default: wait for spot to return
        return ClusterType.NONE