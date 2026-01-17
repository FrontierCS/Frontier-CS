import json
from argparse import Namespace
from collections import deque
from typing import List, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "adaptive_spot_dominance"

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
        
        self.cost_spot = 0.9701
        self.cost_ondemand = 3.06
        self.cost_ratio = self.cost_ondemand / self.cost_spot
        
        self.work_remaining = self.task_duration
        self.current_region = 0
        self.region_history = deque(maxlen=10)
        self.spot_streak = 0
        self.ondemand_streak = 0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        self.work_remaining = self.task_duration - sum(self.task_done_time)
        
        if self.work_remaining <= 0:
            return ClusterType.NONE
        
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        required_steps = (self.work_remaining + gap - 1) // gap
        
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        current_region = self.env.get_current_region()
        
        safe_time_needed = required_steps * gap + overhead
        if time_left < safe_time_needed:
            return ClusterType.ON_DEMAND
        
        if has_spot:
            if last_cluster_type == ClusterType.SPOT:
                self.spot_streak += 1
                self.ondemand_streak = 0
            else:
                self.spot_streak = 1
            
            buffer_factor = min(2.0, max(1.0, self.cost_ratio / 2))
            buffer_steps = int(buffer_factor * self.spot_streak)
            
            if buffer_steps < 5 or self.spot_streak % buffer_steps != 0:
                return ClusterType.SPOT
        else:
            self.spot_streak = 0
            if last_cluster_type != ClusterType.ON_DEMAND:
                self.ondemand_streak = 1
            else:
                self.ondemand_streak += 1
            
            if self.ondemand_streak > 3:
                return ClusterType.NONE
        
        if not has_spot and last_cluster_type == ClusterType.SPOT:
            num_regions = self.env.get_num_regions()
            if num_regions > 1:
                best_region = current_region
                best_score = -1
                
                for r in range(num_regions):
                    if r == current_region:
                        continue
                    
                    self.region_history.append(r)
                    recent_count = sum(1 for reg in self.region_history if reg == r)
                    
                    score = 1.0 / (recent_count + 1)
                    if score > best_score:
                        best_score = score
                        best_region = r
                
                if best_region != current_region:
                    self.env.switch_region(best_region)
                    self.current_region = best_region
                    return ClusterType.NONE
        
        if not has_spot and time_left > required_steps * gap * 1.5:
            return ClusterType.NONE
        
        return ClusterType.ON_DEMAND