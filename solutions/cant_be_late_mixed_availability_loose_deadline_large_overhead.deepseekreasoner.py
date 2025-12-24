import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.spot_availability_history = []
        self.spot_price = 0.97
        self.ondemand_price = 3.06
        self.remaining_work = 0.0
        self.time_remaining = 0.0
        self.safety_factor = 2.0
        self.min_spot_confidence = 0.3
        self.consecutive_spot_runs = 0
        self.consecutive_ondemand_runs = 0
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def _update_state(self, has_spot: bool):
        self.spot_availability_history.append(1 if has_spot else 0)
        if len(self.spot_availability_history) > 100:
            self.spot_availability_history.pop(0)
            
        self.remaining_work = self.task_duration - sum(self.task_done_time)
        self.time_remaining = self.deadline - self.env.elapsed_seconds
        
    def _spot_availability_probability(self, lookback: int = 20) -> float:
        if not self.spot_availability_history:
            return 0.0
        recent = self.spot_availability_history[-lookback:]
        return sum(recent) / len(recent) if recent else 0.0
    
    def _compute_aggressiveness(self) -> float:
        time_needed_with_overhead = self.remaining_work + self.restart_overhead
        slack_ratio = (self.time_remaining - time_needed_with_overhead) / self.time_remaining
        
        if slack_ratio > 0.3:
            return 0.9
        elif slack_ratio > 0.1:
            return 0.7
        elif slack_ratio > -0.1:
            return 0.4
        else:
            return 0.1
    
    def _should_use_spot(self, has_spot: bool, spot_prob: float) -> bool:
        if not has_spot:
            return False
            
        min_work_for_spot = self.restart_overhead * 2.0
        if self.remaining_work < min_work_for_spot:
            return False
            
        if self.time_remaining < self.remaining_work + self.restart_overhead * 3:
            return False
            
        if spot_prob < self.min_spot_confidence:
            return False
            
        aggressiveness = self._compute_aggressiveness()
        required_confidence = 1.0 - aggressiveness
        
        return spot_prob > required_confidence
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_state(has_spot)
        spot_prob = self._spot_availability_probability()
        
        if self.remaining_work <= 0:
            return ClusterType.NONE
            
        if self.time_remaining <= 0:
            return ClusterType.NONE
            
        time_needed_with_overhead = self.remaining_work + self.restart_overhead
        
        if self.time_remaining < time_needed_with_overhead * 0.8:
            if last_cluster_type == ClusterType.ON_DEMAND:
                self.consecutive_ondemand_runs += 1
                return ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        if self.time_remaining < self.remaining_work * 1.2:
            return ClusterType.ON_DEMAND
        
        if self._should_use_spot(has_spot, spot_prob):
            if last_cluster_type == ClusterType.SPOT:
                self.consecutive_spot_runs += 1
                if self.consecutive_spot_runs > 5:
                    self.consecutive_spot_runs = 0
                    self.consecutive_ondemand_runs = 0
                    return ClusterType.ON_DEMAND
            else:
                self.consecutive_spot_runs = 1
                self.consecutive_ondemand_runs = 0
            return ClusterType.SPOT
        else:
            if last_cluster_type == ClusterType.ON_DEMAND:
                self.consecutive_ondemand_runs += 1
                if self.consecutive_ondemand_runs > 3 and has_spot:
                    self.consecutive_ondemand_runs = 0
                    return ClusterType.SPOT
            else:
                self.consecutive_ondemand_runs = 1
                self.consecutive_spot_runs = 0
            return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
