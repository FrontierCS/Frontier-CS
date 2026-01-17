import json
from argparse import Namespace
from typing import List, Tuple, Optional
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

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
        
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.total_regions = 0
        self.region_history = []
        self.last_region = 0
        self.consecutive_spot_failures = 0
        self.max_spot_failures = 3
        self.emergency_threshold = 0.3
        self.safety_margin = 0.1
        
        return self

    def _get_remaining_work(self) -> float:
        """Calculate remaining work in seconds."""
        return self.task_duration - sum(self.task_done_time)

    def _get_time_remaining(self) -> float:
        """Calculate time remaining until deadline."""
        return self.deadline - self.env.elapsed_seconds

    def _get_critical_ratio(self) -> float:
        """Calculate ratio of remaining work to remaining time."""
        remaining_work = self._get_remaining_work()
        time_remaining = self._get_time_remaining()
        if time_remaining <= 0:
            return float('inf')
        return remaining_work / time_remaining

    def _should_use_ondemand(self) -> bool:
        """Determine if we should switch to on-demand."""
        if self._get_remaining_work() <= 0:
            return False
            
        remaining_work = self._get_remaining_work()
        time_remaining = self._get_time_remaining()
        
        if time_remaining <= 0:
            return True
            
        if self.remaining_restart_overhead > 0:
            remaining_work += self.remaining_restart_overhead
            
        required_time = remaining_work + self.restart_overhead
        
        if required_time > time_remaining * (1 - self.safety_margin):
            return True
            
        critical_ratio = self._get_critical_ratio()
        if critical_ratio > self.emergency_threshold:
            return True
            
        if self.consecutive_spot_failures >= self.max_spot_failures:
            return True
            
        return False

    def _choose_best_region(self, has_spot: bool) -> int:
        """Choose the best region to run in."""
        if self.total_regions == 0:
            self.total_regions = self.env.get_num_regions()
            
        current_region = self.env.get_current_region()
        
        if has_spot:
            return current_region
            
        for region in range(self.total_regions):
            if region != current_region:
                return region
                
        return current_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self._get_remaining_work() <= 0:
            return ClusterType.NONE
            
        if self.total_regions == 0:
            self.total_regions = self.env.get_num_regions()
            self.last_region = self.env.get_current_region()
        
        current_region = self.env.get_current_region()
        
        if self.last_region != current_region:
            self.consecutive_spot_failures = 0
            self.last_region = current_region
        
        if not has_spot:
            self.consecutive_spot_failures += 1
        else:
            self.consecutive_spot_failures = 0
        
        if self._should_use_ondemand():
            best_region = self._choose_best_region(has_spot)
            if best_region != current_region:
                self.env.switch_region(best_region)
                self.last_region = best_region
                self.consecutive_spot_failures = 0
            return ClusterType.ON_DEMAND
        
        if has_spot:
            best_region = self._choose_best_region(has_spot)
            if best_region != current_region:
                self.env.switch_region(best_region)
                self.last_region = best_region
                self.consecutive_spot_failures = 0
            return ClusterType.SPOT
        
        best_region = self._choose_best_region(has_spot)
        if best_region != current_region:
            self.env.switch_region(best_region)
            self.last_region = best_region
            self.consecutive_spot_failures = 0
            
            current_has_spot = has_spot
            if self.total_regions > 1:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND if self._should_use_ondemand() else ClusterType.NONE
        else:
            if self.consecutive_spot_failures >= self.max_spot_failures:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE