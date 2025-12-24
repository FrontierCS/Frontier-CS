import json
from argparse import Namespace
from typing import List
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"

    def __init__(self, args):
        super().__init__(args)
        self.region_count = 0
        self.time_step = 0
        self.spot_prices = []
        self.on_demand_prices = []
        self.region_reliability = []
        self.spot_history = []
        self.consecutive_failures = 0
        self.last_spot_available = True
        self.safe_threshold = 0.8
        self.min_spot_usage = 0.3
        self.max_consecutive_switches = 3
        self.switch_counter = 0
        self.last_decision = None
        self.emergency_mode = False

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
        
        self.region_count = self.env.get_num_regions() if hasattr(self.env, 'get_num_regions') else 1
        self.time_step = self.env.gap_seconds if hasattr(self.env, 'gap_seconds') else 3600.0
        
        self.spot_prices = [0.9701] * self.region_count
        self.on_demand_prices = [3.06] * self.region_count
        self.region_reliability = [0.5] * self.region_count
        self.spot_history = [[] for _ in range(self.region_count)]
        
        return self

    def _calculate_remaining_time(self) -> float:
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        return max(0.0, remaining_time)

    def _calculate_progress(self) -> float:
        total_done = sum(self.task_done_time)
        progress = total_done / self.task_duration
        return progress

    def _calculate_required_rate(self) -> float:
        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_time = self._calculate_remaining_time()
        
        if remaining_time <= 0:
            return float('inf')
        
        required_rate = remaining_work / remaining_time
        return required_rate

    def _estimate_region_reliability(self, region_idx: int, has_spot: bool) -> float:
        if len(self.spot_history[region_idx]) < 10:
            return 0.5
        
        recent_history = self.spot_history[region_idx][-10:]
        reliability = sum(recent_history) / len(recent_history)
        return reliability

    def _find_best_region(self, current_region: int, has_spot: bool) -> int:
        best_region = current_region
        best_score = -float('inf')
        
        for region in range(self.region_count):
            if region == current_region:
                continue
                
            reliability = self._estimate_region_reliability(region, has_spot)
            score = reliability - (abs(region - current_region) * 0.1)
            
            if score > best_score:
                best_score = score
                best_region = region
        
        return best_region

    def _should_switch_region(self, current_region: int, has_spot: bool) -> bool:
        if self.region_count <= 1:
            return False
            
        if self.switch_counter >= self.max_consecutive_switches:
            return False
            
        remaining_time = self._calculate_remaining_time()
        progress = self._calculate_progress()
        
        if not has_spot and self.last_spot_available:
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = max(0, self.consecutive_failures - 1)
        
        reliability = self._estimate_region_reliability(current_region, has_spot)
        
        switch_threshold = 0.3 + (progress * 0.3)
        
        if self.consecutive_failures >= 2:
            return True
            
        if remaining_time < 4 * 3600:
            return False
            
        if reliability < switch_threshold:
            return True
            
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        
        if hasattr(self.env, 'gap_seconds'):
            self.time_step = self.env.gap_seconds
            
        if current_region < len(self.spot_history):
            self.spot_history[current_region].append(1.0 if has_spot else 0.0)
            if len(self.spot_history[current_region]) > 100:
                self.spot_history[current_region] = self.spot_history[current_region][-100:]
        
        remaining_time = self._calculate_remaining_time()
        progress = self._calculate_progress()
        required_rate = self._calculate_required_rate()
        
        if remaining_time <= 0:
            return ClusterType.NONE
        
        if self.remaining_restart_overhead > 0:
            self.switch_counter = 0
            return ClusterType.NONE
        
        if progress >= 1.0:
            return ClusterType.NONE
        
        remaining_work = self.task_duration - sum(self.task_done_time)
        time_needed_with_overhead = remaining_work + self.restart_overhead
        
        if remaining_time < time_needed_with_overhead:
            self.emergency_mode = True
        
        if self.emergency_mode:
            if has_spot and self.consecutive_failures < 2:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        
        if self._should_switch_region(current_region, has_spot):
            best_region = self._find_best_region(current_region, has_spot)
            if best_region != current_region:
                self.env.switch_region(best_region)
                self.switch_counter += 1
                self.consecutive_failures = 0
                return ClusterType.NONE
        
        if self.switch_counter > 0 and has_spot:
            self.switch_counter = max(0, self.switch_counter - 1)
        
        time_critical = remaining_time < 8 * 3600
        
        if time_critical:
            if required_rate > 0.9:
                return ClusterType.ON_DEMAND
            elif has_spot and self.consecutive_failures < 2:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        
        aggressive_mode = progress < 0.7 and remaining_time > 24 * 3600
        
        if aggressive_mode:
            if has_spot and self.consecutive_failures < 3:
                return ClusterType.SPOT
            else:
                if remaining_time < 12 * 3600:
                    return ClusterType.ON_DEMAND
                return ClusterType.NONE
        
        conservative_threshold = 0.6 - (progress * 0.2)
        reliability = self._estimate_region_reliability(current_region, has_spot)
        
        if has_spot and reliability > conservative_threshold and self.consecutive_failures < 2:
            if progress > 0.85 and remaining_time > 6 * 3600:
                return ClusterType.SPOT
            elif progress > 0.6:
                if remaining_time > 8 * 3600:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                return ClusterType.SPOT
        else:
            if remaining_time < 6 * 3600 or required_rate > 0.7:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE
