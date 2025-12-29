import json
from argparse import Namespace
from collections import defaultdict
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "multi_region_adaptive"

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
        
        self.region_stats = defaultdict(lambda: {"spot_available": 0, "total_checks": 0})
        self.last_action = None
        self.consecutive_spot_failures = 0
        self.spot_attempts = 0
        self.region_switches = 0
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.price_ratio = self.ondemand_price / self.spot_price
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        self.region_stats[current_region]["total_checks"] += 1
        if has_spot:
            self.region_stats[current_region]["spot_available"] += 1
        
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration[0] - work_done
        
        if work_remaining <= 0:
            return ClusterType.NONE
        
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        time_per_step = self.env.gap_seconds
        overhead = self.restart_overhead[0]
        
        required_steps = math.ceil(work_remaining / time_per_step)
        available_steps = math.floor(remaining_time / time_per_step)
        
        if required_steps > available_steps:
            return ClusterType.ON_DEMAND
        
        spot_prob = 0.0
        if self.region_stats[current_region]["total_checks"] > 0:
            spot_prob = (self.region_stats[current_region]["spot_available"] / 
                        self.region_stats[current_region]["total_checks"])
        
        time_pressure = 1.0 - (remaining_time / self.deadline) if self.deadline > 0 else 0
        work_pressure = 1.0 - (work_done / self.task_duration[0]) if self.task_duration[0] > 0 else 0
        
        urgency = max(time_pressure, work_pressure)
        
        spot_score = spot_prob * self.price_ratio - urgency * 0.5
        ondemand_score = 1.0 - urgency * 0.3
        none_score = 0.0
        
        if has_spot and spot_score > 0:
            self.consecutive_spot_failures = 0
            self.spot_attempts += 1
            self.last_action = ClusterType.SPOT
            return ClusterType.SPOT
        
        if not has_spot and self.last_action == ClusterType.SPOT:
            self.consecutive_spot_failures += 1
        
        critical_time = remaining_time < work_remaining * 2 + overhead * 2
        
        if critical_time:
            self.last_action = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        if self.consecutive_spot_failures >= 2:
            best_region = current_region
            best_prob = spot_prob
            
            for region in range(num_regions):
                if region == current_region:
                    continue
                total = self.region_stats[region]["total_checks"]
                if total > 0:
                    prob = self.region_stats[region]["spot_available"] / total
                    if prob > best_prob:
                        best_prob = prob
                        best_region = region
            
            if best_region != current_region and best_prob > spot_prob + 0.1:
                self.env.switch_region(best_region)
                self.region_switches += 1
                self.consecutive_spot_failures = 0
                self.last_action = None
                return ClusterType.NONE
        
        if ondemand_score > none_score + 0.2 and urgency > 0.3:
            self.last_action = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        self.last_action = ClusterType.NONE
        return ClusterType.NONE