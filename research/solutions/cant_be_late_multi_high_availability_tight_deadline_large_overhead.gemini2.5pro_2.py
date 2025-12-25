import json
from argparse import Namespace
import collections

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "adaptive_ema_v1"

    SAFETY_BUFFER = 1.20
    MAX_WAIT_STEPS = 1
    EMA_ALPHA = 0.1
    SWITCH_THRESHOLD = 0.2

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

        self.num_regions = len(config["trace_files"])
        initial_availability = 0.5
        self.ema_spot_availability = [initial_availability] * self.num_regions
        self.consecutive_outages = [0] * self.num_regions

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        self._update_region_stats(current_region, has_spot)

        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE

        if self._is_urgent(remaining_work):
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        else:
            return self._handle_spot_outage(current_region)

    def _update_region_stats(self, current_region: int, has_spot: bool):
        spot_now = 1.0 if has_spot else 0.0
        current_ema = self.ema_spot_availability[current_region]
        self.ema_spot_availability[current_region] = (
            self.EMA_ALPHA * spot_now + (1 - self.EMA_ALPHA) * current_ema
        )

        if has_spot:
            self.consecutive_outages[current_region] = 0
        else:
            self.consecutive_outages[current_region] += 1

    def _is_urgent(self, remaining_work: float) -> bool:
        remaining_time = self.deadline - self.env.elapsed_seconds
        effective_remaining_time = remaining_time - self.remaining_restart_overhead
        on_demand_finish_time = remaining_work
        return effective_remaining_time < on_demand_finish_time * self.SAFETY_BUFFER

    def _handle_spot_outage(self, current_region: int) -> ClusterType:
        if self.consecutive_outages[current_region] <= self.MAX_WAIT_STEPS:
            return ClusterType.NONE

        best_alt_region, best_alt_ema = self._find_best_alternative_region(
            current_region
        )

        current_ema = self.ema_spot_availability[current_region]

        if best_alt_region != -1 and best_alt_ema > current_ema + self.SWITCH_THRESHOLD:
            self.env.switch_region(best_alt_region)
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.ON_DEMAND

    def _find_best_alternative_region(self, current_region: int) -> tuple[int, float]:
        best_region = -1
        best_ema = -1.0

        for i in range(self.num_regions):
            if i == current_region:
                continue
            if self.ema_spot_availability[i] > best_ema:
                best_ema = self.ema_spot_availability[i]
                best_region = i

        return best_region, best_ema
