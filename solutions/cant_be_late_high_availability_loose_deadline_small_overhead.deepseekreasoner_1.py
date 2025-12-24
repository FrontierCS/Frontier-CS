import math
import json
from typing import List
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.config = None
        self.spot_price = 0.97
        self.ondemand_price = 3.06
        self.restart_penalty = 0.05 * 3600  # 0.05 hours to seconds
        self.critical_threshold = 0.2
        self.conservative_threshold = 0.4
        
    def solve(self, spec_path: str) -> "Solution":
        try:
            with open(spec_path, 'r') as f:
                self.config = json.load(f)
        except:
            pass
        return self
    
    def _get_remaining_work(self) -> float:
        if not self.task_done_time:
            return self.task_duration
        return max(0.0, self.task_duration - sum(self.task_done_time))
    
    def _get_time_to_deadline(self) -> float:
        return max(0.0, self.deadline - self.env.elapsed_seconds)
    
    def _get_required_rate(self) -> float:
        remaining_work = self._get_remaining_work()
        time_left = self._get_time_to_deadline()
        if time_left <= 0:
            return float('inf')
        return remaining_work / time_left
    
    def _is_critical(self) -> bool:
        remaining_work = self._get_remaining_work()
        time_left = self._get_time_to_deadline()
        
        if time_left <= 0:
            return True
            
        required_rate = remaining_work / time_left
        
        safety_margin = self.restart_overhead * 2
        conservative_needed = remaining_work / (time_left - safety_margin)
        
        return required_rate > self.critical_threshold or conservative_needed > self.conservative_threshold
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining_work = self._get_remaining_work()
        time_left = self._get_time_to_deadline()
        
        if remaining_work <= 0:
            return ClusterType.NONE
            
        if time_left <= 0:
            return ClusterType.ON_DEMAND
        
        required_rate = self._get_required_rate()
        
        critical = self._is_critical()
        
        if critical:
            if last_cluster_type == ClusterType.SPOT and not has_spot:
                return ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        if not has_spot:
            if required_rate > 0.1:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE
        
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            if required_rate > 0.15:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE
        
        if time_left - remaining_work > self.restart_overhead * 5:
            return ClusterType.SPOT
        
        if required_rate < 0.05:
            return ClusterType.NONE
        
        return ClusterType.SPOT
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
