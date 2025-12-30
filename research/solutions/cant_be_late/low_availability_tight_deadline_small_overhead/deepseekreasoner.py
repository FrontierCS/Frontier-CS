import os
import json
import math
from enum import Enum
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args=None):
        super().__init__(args)
        self.config = {}
        self.remaining_work = 0.0
        self.last_spot_used = False
        self.restart_timer = 0.0
        self.work_segments = []
        self.current_progress = 0.0
        self.time_since_spot = 0.0
        self.conservative_mode = False
        self.emergency_mode = False
        
    def solve(self, spec_path: str) -> "Solution":
        if os.path.exists(spec_path):
            with open(spec_path, 'r') as f:
                self.config = json.load(f)
        self.work_segments = []
        self.current_progress = 0.0
        self.restart_timer = 0.0
        self.last_spot_used = False
        self.remaining_work = 0.0
        self.time_since_spot = 0.0
        self.conservative_mode = False
        self.emergency_mode = False
        return self
    
    def _calculate_remaining_work(self) -> float:
        total_done = sum(end - start for start, end in self.task_done_time)
        return max(0.0, self.task_duration - total_done)
    
    def _calculate_time_until_deadline(self) -> float:
        return max(0.0, self.deadline - self.env.elapsed_seconds)
    
    def _calculate_critical_time(self, remaining_work: float) -> float:
        safety_margin = self.restart_overhead * 2.0
        return remaining_work + safety_margin
    
    def _calculate_progress_rate(self) -> float:
        if not self.task_done_time:
            return 0.0
        total_duration = sum(end - start for start, end in self.task_done_time)
        return total_duration / max(1.0, self.env.elapsed_seconds)
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        time_step = self.env.gap_seconds
        current_time = self.env.elapsed_seconds
        
        remaining_work = self._calculate_remaining_work()
        time_until_deadline = self._calculate_time_until_deadline()
        
        if remaining_work <= 0.0:
            return ClusterType.NONE
        
        critical_time = self._calculate_critical_time(remaining_work)
        
        self.remaining_work = remaining_work
        self.conservative_mode = time_until_deadline < critical_time * 1.5
        self.emergency_mode = time_until_deadline < critical_time
        
        if self.restart_timer > 0:
            self.restart_timer -= time_step
            if self.restart_timer < 0:
                self.restart_timer = 0.0
        
        if last_cluster_type == ClusterType.SPOT:
            self.time_since_spot = 0.0
            self.last_spot_used = True
        else:
            self.time_since_spot += time_step
        
        if self.emergency_mode:
            return ClusterType.ON_DEMAND
        
        if has_spot:
            if self.restart_timer <= 0:
                spot_run_time = 3600.0
                if self.conservative_mode:
                    spot_run_time = 1800.0
                
                if self.time_since_spot > 3600.0:
                    return ClusterType.SPOT
                
                if remaining_work > 4 * 3600.0:
                    run_spot = True
                    if last_cluster_type != ClusterType.SPOT:
                        run_spot = remaining_work > self.restart_overhead + 1800.0
                    if run_spot:
                        return ClusterType.SPOT
        
        if self.conservative_mode:
            return ClusterType.ON_DEMAND
        
        if not has_spot:
            if time_until_deadline > remaining_work * 1.2:
                return ClusterType.NONE
        
        return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)