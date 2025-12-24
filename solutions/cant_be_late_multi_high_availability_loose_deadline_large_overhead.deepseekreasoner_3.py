import json
import math
from argparse import Namespace
from collections import deque
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType

class Solution(MultiRegionStrategy):
    NAME = "my_strategy"
    
    def __init__(self, args):
        super().__init__(args)
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.spot_cost_per_step = self.spot_price * self.env.gap_seconds / 3600.0
        self.ondemand_cost_per_step = self.ondemand_price * self.env.gap_seconds / 3600.0
        self.region_data = None
        self.region_count = 0
        self.time_steps = 0
        self.strategy_initialized = False
        self.current_plan = deque()
        
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
        return self
    
    def _initialize_strategy(self):
        if self.strategy_initialized:
            return
        
        self.region_count = self.env.get_num_regions()
        self.time_steps = int(self.deadline / self.env.gap_seconds) + 1
        
        self.strategy_initialized = True
        self._generate_execution_plan()
    
    def _generate_execution_plan(self):
        work_remaining = self.task_duration
        time_remaining = self.deadline
        current_region = 0
        
        while work_remaining > 0 and time_remaining > 0:
            steps_needed = math.ceil(work_remaining / self.env.gap_seconds)
            
            if time_remaining < work_remaining + self.restart_overhead:
                self.current_plan.append((current_region, ClusterType.ON_DEMAND))
                work_remaining -= min(self.env.gap_seconds, work_remaining)
                time_remaining -= self.env.gap_seconds
            else:
                slack_ratio = time_remaining / (work_remaining + self.restart_overhead)
                
                if slack_ratio > 1.5:
                    self.current_plan.append((current_region, ClusterType.SPOT))
                    work_remaining -= min(self.env.gap_seconds, work_remaining)
                    time_remaining -= self.env.gap_seconds
                else:
                    if self.env.get_current_region() != current_region:
                        self.current_plan.append((current_region, ClusterType.NONE))
                        time_remaining -= self.env.gap_seconds
                    else:
                        self.current_plan.append((current_region, ClusterType.ON_DEMAND))
                        work_remaining -= min(self.env.gap_seconds, work_remaining)
                        time_remaining -= self.env.gap_seconds
        
        while time_remaining > 0:
            self.current_plan.append((current_region, ClusterType.NONE))
            time_remaining -= self.env.gap_seconds
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_strategy()
        
        if not self.current_plan:
            self._generate_execution_plan()
        
        elapsed_steps = int(self.env.elapsed_seconds / self.env.gap_seconds)
        
        if elapsed_steps >= len(self.current_plan):
            return ClusterType.NONE
        
        planned_region, planned_action = self.current_plan[elapsed_steps]
        
        current_region = self.env.get_current_region()
        if current_region != planned_region:
            self.env.switch_region(planned_region)
        
        if planned_action == ClusterType.SPOT and not has_spot:
            return ClusterType.ON_DEMAND
        
        return planned_action
