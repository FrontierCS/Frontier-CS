import json
import os
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__(args)
        self.preempted = False
        self.restart_timer = 0
        self.conservative_threshold = 1.1
        self.min_spot_ratio = 0.3
        self.time_step = 0
        self.use_on_demand_count = 0
        self.total_steps_estimated = 0
        self.safety_factor = 1.2

    def solve(self, spec_path: str) -> "Solution":
        if os.path.exists(spec_path):
            try:
                with open(spec_path) as f:
                    config = json.load(f)
                self.conservative_threshold = config.get("conservative_threshold", 1.1)
                self.min_spot_ratio = config.get("min_spot_ratio", 0.3)
                self.safety_factor = config.get("safety_factor", 1.2)
            except:
                pass
        self.time_step = 0
        self.use_on_demand_count = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self.time_step += 1
        
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        if work_remaining <= 0:
            return ClusterType.NONE
        
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.preempted = True
        
        if self.restart_timer > 0:
            self.restart_timer -= self.env.gap_seconds
        
        progress_per_step = self.env.gap_seconds
        if last_cluster_type == ClusterType.SPOT and self.restart_timer > 0:
            progress_per_step = 0
        
        required_steps = work_remaining / progress_per_step if progress_per_step > 0 else float('inf')
        available_steps = time_remaining / self.env.gap_seconds
        
        if self.total_steps_estimated == 0:
            self.total_steps_estimated = required_steps
        
        spot_ratio = self.min_spot_ratio
        if available_steps > 0:
            required_ratio = required_steps / available_steps
            spot_ratio = max(self.min_spot_ratio, 
                           1.0 - (required_ratio * self.conservative_threshold))
        
        use_spot = (has_spot and not self.preempted and 
                   self.restart_timer <= 0 and
                   self.time_step % 100 < spot_ratio * 100)
        
        if use_spot:
            if self.preempted:
                self.restart_timer = self.restart_overhead
                self.preempted = False
            return ClusterType.SPOT
        
        if work_remaining > 0 and time_remaining <= work_remaining * self.safety_factor:
            return ClusterType.ON_DEMAND
        
        if time_remaining <= self.restart_overhead * 2:
            return ClusterType.ON_DEMAND
        
        if not has_spot:
            return ClusterType.ON_DEMAND if work_remaining > 0 else ClusterType.NONE
        
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)