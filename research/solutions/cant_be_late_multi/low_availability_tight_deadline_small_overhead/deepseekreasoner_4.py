import json
import math
from argparse import Namespace
from typing import List, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cbl_strategy"

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

        self.on_demand_price = 3.06
        self.spot_price = 0.9701
        self.price_ratio = self.on_demand_price / self.spot_price

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()

        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        task_duration = self.task_duration

        work_done = sum(self.task_done_time)
        work_remaining = task_duration - work_done
        time_remaining = deadline - elapsed

        if work_remaining <= 0:
            return ClusterType.NONE

        overhead = self.restart_overhead
        gap = self.env.gap_seconds

        critical_ratio = work_remaining / max(time_remaining, 0.001)

        if critical_ratio > 1.0:
            must_use_od = True
        elif critical_ratio > 0.8:
            must_use_od = not has_spot
        else:
            must_use_od = False

        if must_use_od:
            if last_cluster_type != ClusterType.ON_DEMAND:
                best_region = self._find_best_region_for_od()
                if best_region != current_region:
                    self.env.switch_region(best_region)
            return ClusterType.ON_DEMAND

        if has_spot:
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            else:
                if self.remaining_restart_overhead > 0:
                    remaining_overhead = self.remaining_restart_overhead
                else:
                    remaining_overhead = overhead

                effective_time = gap - remaining_overhead
                if effective_time <= 0:
                    return ClusterType.NONE

                expected_work = min(effective_time, work_remaining)
                expected_cost = self.spot_price * (gap / 3600.0)

                cost_per_work = expected_cost / expected_work if expected_work > 0 else float('inf')

                od_expected_work = min(gap, work_remaining)
                od_cost = self.on_demand_price * (gap / 3600.0)
                od_cost_per_work = od_cost / od_expected_work if od_expected_work > 0 else float('inf')

                if cost_per_work < od_cost_per_work and expected_work > 0:
                    return ClusterType.SPOT
                else:
                    if last_cluster_type != ClusterType.ON_DEMAND:
                        best_region = self._find_best_region_for_od()
                        if best_region != current_region:
                            self.env.switch_region(best_region)
                    return ClusterType.ON_DEMAND

        best_region, spot_available = self._find_best_spot_region()

        if spot_available:
            if best_region != current_region:
                self.env.switch_region(best_region)
            return ClusterType.SPOT

        best_region = self._find_best_region_for_od()
        if best_region != current_region:
            self.env.switch_region(best_region)
        return ClusterType.ON_DEMAND

    def _find_best_spot_region(self) -> Tuple[int, bool]:
        num_regions = self.env.get_num_regions()
        current_region = self.env.get_current_region()

        best_region = current_region
        best_score = -1.0
        any_spot = False

        for region in range(num_regions):
            if region == current_region:
                continue

            try:
                self.env.switch_region(region)
                self.env.switch_region(current_region)

                score = self._evaluate_region(region)
                if score > best_score:
                    best_score = score
                    best_region = region
                    any_spot = True
            except:
                continue

        self.env.switch_region(current_region)
        return best_region, any_spot

    def _find_best_region_for_od(self) -> int:
        num_regions = self.env.get_num_regions()
        current_region = self.env.get_current_region()

        best_region = current_region
        best_score = self._evaluate_region(current_region)

        for region in range(num_regions):
            if region == current_region:
                continue

            try:
                score = self._evaluate_region(region)
                if score > best_score:
                    best_score = score
                    best_region = region
            except:
                continue

        return best_region

    def _evaluate_region(self, region: int) -> float:
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - self.env.elapsed_seconds

        if time_remaining <= 0 or work_remaining <= 0:
            return 0.0

        critical_ratio = work_remaining / time_remaining
        return 1.0 / (critical_ratio + 0.1)