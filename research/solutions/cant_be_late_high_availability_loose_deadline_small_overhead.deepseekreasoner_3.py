import numpy as np
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_slack_controller"

    def __init__(self, args):
        super().__init__(args)
        self._init_params()

    def _init_params(self):
        self.spot_price = 0.97
        self.ondemand_price = 3.06
        self.price_ratio = self.spot_price / self.ondemand_price
        self.restart_overhead_hrs = 0.05
        
        self.min_spot_prob = 0.43
        self.max_spot_prob = 0.78
        self.avg_spot_prob = (self.min_spot_prob + self.max_spot_prob) / 2
        
        self.task_hours = 48.0
        self.deadline_hours = 70.0
        self.max_slack = 22.0
        
        self.aggressiveness = 0.75
        self.safety_margin = 0.1
        self.urgent_threshold = 0.15
        
        self.last_action = None
        self.consecutive_none = 0
        self.remaining_work_cache = None
        self.time_buffer = 0.0
        self.spot_unavailable_streak = 0
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def _estimate_remaining_work(self) -> float:
        if self.task_done_time:
            completed = sum(segment[1] - segment[0] for segment in self.task_done_time)
            remaining = self.task_duration - completed
            return max(0.0, remaining)
        return self.task_duration
    
    def _calculate_time_pressure(self, remaining_work: float) -> float:
        elapsed = self.env.elapsed_seconds / 3600.0
        remaining_time = self.deadline / 3600.0 - elapsed
        if remaining_time <= 0:
            return float('inf')
        
        min_time_needed = remaining_work
        if remaining_time <= min_time_needed:
            return float('inf')
        
        return min_time_needed / remaining_time
    
    def _should_use_ondemand(self, pressure: float, has_spot: bool) -> bool:
        if pressure > 0.8:
            return True
        
        if not has_spot:
            if self.spot_unavailable_streak > 5:
                return pressure > 0.3
            return pressure > 0.6
        
        expected_spot_time = remaining_work = self._estimate_remaining_work()
        expected_spot_time /= self.avg_spot_prob
        expected_ondemand_time = remaining_work
        
        elapsed = self.env.elapsed_seconds / 3600.0
        remaining_time = self.deadline / 3600.0 - elapsed
        
        if expected_spot_time + self.restart_overhead_hrs * 2 > remaining_time:
            return True
        
        if expected_ondemand_time + self.safety_margin > remaining_time:
            return True
        
        return False
    
    def _should_pause(self, pressure: float, has_spot: bool, last_cluster_type: ClusterType) -> bool:
        if pressure > 0.9:
            return False
        
        if not has_spot:
            if pressure < 0.2:
                return True
            if last_cluster_type == ClusterType.NONE and self.consecutive_none < 10:
                return True
        
        elapsed = self.env.elapsed_seconds / 3600.0
        if elapsed < self.task_hours * 0.1:
            return False
        
        remaining_work = self._estimate_remaining_work()
        if remaining_work < self.task_hours * 0.1:
            return False
        
        if pressure < 0.3 and has_spot:
            return False
        
        return pressure < 0.4 and last_cluster_type == ClusterType.NONE and self.consecutive_none < 5
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining_work = self._estimate_remaining_work()
        
        if remaining_work <= 0:
            return ClusterType.NONE
        
        pressure = self._calculate_time_pressure(remaining_work)
        
        if pressure >= 1.0:
            return ClusterType.ON_DEMAND
        
        if not has_spot:
            self.spot_unavailable_streak += 1
        else:
            self.spot_unavailable_streak = 0
        
        if self._should_use_ondemand(pressure, has_spot):
            self.consecutive_none = 0
            return ClusterType.ON_DEMAND
        
        if has_spot:
            if self._should_pause(pressure, has_spot, last_cluster_type):
                self.consecutive_none += 1
                return ClusterType.NONE
            else:
                self.consecutive_none = 0
                return ClusterType.SPOT
        else:
            if self._should_pause(pressure, has_spot, last_cluster_type):
                self.consecutive_none += 1
                return ClusterType.NONE
            else:
                self.consecutive_none = 0
                return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)