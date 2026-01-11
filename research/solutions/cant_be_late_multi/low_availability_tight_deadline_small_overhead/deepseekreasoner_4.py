import json
from argparse import Namespace
from typing import List
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "adaptive_scheduler"
    
    def __init__(self, args):
        super().__init__(args)
        self.region_history = []
        self.consecutive_none = 0
        self.spot_use_count = 0
        self.od_use_count = 0
        
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
        
        self.safety_margin = max(2.0 * self.restart_overhead, 3600.0)
        self.initial_task_duration = self.task_duration
        self.last_region = -1
        self.region_spot_history = {}
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        
        if current_region not in self.region_spot_history:
            self.region_spot_history[current_region] = []
        self.region_spot_history[current_region].append(1 if has_spot else 0)
        
        if len(self.region_spot_history[current_region]) > 10:
            self.region_spot_history[current_region] = self.region_spot_history[current_region][-10:]
        
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        if remaining_work <= 0:
            return ClusterType.NONE
            
        if remaining_time <= 0:
            return ClusterType.NONE
        
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        time_per_step = self.env.gap_seconds
        needed_steps = math.ceil(remaining_work / time_per_step)
        max_wait_steps = int(remaining_time / time_per_step) - needed_steps
        
        if remaining_time < remaining_work + self.safety_margin:
            if has_spot and remaining_time > remaining_work + self.restart_overhead * 2:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        if max_wait_steps <= 1:
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        if self.last_region != current_region:
            self.consecutive_none = 0
            self.last_region = current_region
        
        spot_availability = sum(self.region_spot_history[current_region]) / len(self.region_spot_history[current_region]) if self.region_spot_history[current_region] else 0
        
        if spot_availability < 0.3 and max_wait_steps > 3:
            best_spot = -1
            best_score = -1
            
            for r in range(self.env.get_num_regions()):
                if r == current_region:
                    continue
                    
                hist = self.region_spot_history.get(r, [])
                if hist:
                    avail = sum(hist) / len(hist)
                    if avail > best_score:
                        best_score = avail
                        best_spot = r
            
            if best_spot != -1 and best_score > spot_availability + 0.2:
                self.env.switch_region(best_spot)
                self.consecutive_none = 0
                return ClusterType.NONE
        
        if has_spot:
            if self.consecutive_none > 2:
                self.consecutive_none = 0
                return ClusterType.SPOT
                
            if remaining_work > time_per_step * 4 and max_wait_steps > 3:
                self.consecutive_none = 0
                return ClusterType.SPOT
            elif remaining_work > time_per_step * 2:
                self.consecutive_none = 0
                return ClusterType.SPOT
        
        if not has_spot and max_wait_steps > 2:
            self.consecutive_none += 1
            if self.consecutive_none > 5:
                self.consecutive_none = 0
                return ClusterType.ON_DEMAND
            return ClusterType.NONE
        
        return ClusterType.ON_DEMAND