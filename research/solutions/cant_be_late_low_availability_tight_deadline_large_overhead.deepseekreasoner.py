import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType
from typing import Optional
import math


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.config = None
        self.required_work = None
        self.spot_availability_history = []
        self.last_decision = None
        self.restart_timer = 0
        self.work_done = 0
        self.spot_price = 0.97
        self.ondemand_price = 3.06
        self.step_hours = 1.0

    def solve(self, spec_path: str) -> "Solution":
        try:
            with open(spec_path, 'r') as f:
                content = f.read()
                if "price_spot" in content:
                    lines = content.strip().split('\n')
                    for line in lines:
                        if "price_spot" in line:
                            self.spot_price = float(line.split('=')[1].strip())
                        elif "price_ondemand" in line:
                            self.ondemand_price = float(line.split('=')[1].strip())
        except Exception:
            pass
        
        self.step_hours = self.env.gap_seconds / 3600.0
        return self

    def _update_state(self):
        self.work_done = sum(self.task_done_time) / 3600.0
        self.required_work = self.task_duration / 3600.0
        elapsed_hours = self.env.elapsed_seconds / 3600.0
        deadline_hours = self.deadline / 3600.0
        return elapsed_hours, deadline_hours

    def _calculate_slack(self, elapsed_hours, deadline_hours):
        work_left = max(0.0, self.required_work - self.work_done)
        time_left = max(0.0, deadline_hours - elapsed_hours)
        
        if work_left <= 0:
            return float('inf')
        if time_left <= 0:
            return float('-inf')
            
        slack = time_left - work_left
        return slack

    def _should_use_ondemand(self, elapsed_hours, deadline_hours):
        work_left = max(0.0, self.required_work - self.work_done)
        time_left = max(0.0, deadline_hours - elapsed_hours)
        
        if work_left <= 0 or time_left <= 0:
            return True
            
        time_per_work_unit = time_left / work_left
        
        if self.restart_timer > 0:
            remaining_restart = self.restart_overhead / 3600.0
            if time_per_work_unit < 1.5:
                return True
        
        if time_per_work_unit < 1.2:
            return True
            
        if work_left > 0 and time_left < work_left + (self.restart_overhead / 3600.0):
            return True
            
        return False

    def _should_pause(self, elapsed_hours, deadline_hours):
        work_left = max(0.0, self.required_work - self.work_done)
        time_left = max(0.0, deadline_hours - elapsed_hours)
        
        if work_left <= 0:
            return True
            
        time_per_work_unit = time_left / work_left if work_left > 0 else float('inf')
        
        if time_per_work_unit > 2.0:
            return True
            
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed_hours, deadline_hours = self._update_state()
        
        if self.restart_timer > 0:
            self.restart_timer -= self.step_hours
            return ClusterType.NONE
        
        self.spot_availability_history.append(has_spot)
        if len(self.spot_availability_history) > 20:
            self.spot_availability_history.pop(0)
        
        spot_availability = sum(self.spot_availability_history) / len(self.spot_availability_history) if self.spot_availability_history else 0
        
        if self._should_use_ondemand(elapsed_hours, deadline_hours):
            if last_cluster_type != ClusterType.ON_DEMAND:
                self.restart_timer = self.restart_overhead / 3600.0
            return ClusterType.ON_DEMAND
        
        if self._should_pause(elapsed_hours, deadline_hours):
            return ClusterType.NONE
        
        if has_spot:
            if last_cluster_type != ClusterType.SPOT:
                self.restart_timer = self.restart_overhead / 3600.0
            return ClusterType.SPOT
        
        if elapsed_hours < deadline_hours * 0.7 and spot_availability < 0.3:
            return ClusterType.NONE
        
        if last_cluster_type != ClusterType.ON_DEMAND:
            self.restart_timer = self.restart_overhead / 3600.0
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)