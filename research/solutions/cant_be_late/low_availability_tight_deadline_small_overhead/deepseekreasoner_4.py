import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.spot_available_buffer = []
        self.spot_pattern_window = 60
        self.min_spot_prob = 0.3
        self.critical_threshold = 0.1
        self.last_decision = ClusterType.NONE
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def _estimate_spot_probability(self, has_spot: bool) -> float:
        self.spot_available_buffer.append(1 if has_spot else 0)
        if len(self.spot_available_buffer) > self.spot_pattern_window:
            self.spot_available_buffer.pop(0)
        
        if len(self.spot_available_buffer) < 10:
            return 0.5 if has_spot else 0.2
        
        recent_available = sum(self.spot_available_buffer[-10:]) / 10.0
        long_term_available = sum(self.spot_available_buffer) / len(self.spot_available_buffer)
        
        return max(self.min_spot_prob, (recent_available * 0.6 + long_term_available * 0.4))
    
    def _calculate_required_progress(self, remaining_time: float, remaining_work: float) -> float:
        if remaining_time <= 0:
            return float('inf')
        return remaining_work / remaining_time
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_time = self.env.elapsed_seconds
        time_step = self.env.gap_seconds
        
        completed_work = sum(self.task_done_time) if self.task_done_time else 0
        remaining_work = self.task_duration - completed_work
        remaining_time = self.deadline - current_time
        
        if remaining_work <= 0:
            return ClusterType.NONE
        
        spot_prob = self._estimate_spot_probability(has_spot)
        
        required_progress_rate = self._calculate_required_progress(
            remaining_time, remaining_work
        )
        
        conservative_factor = 1.2
        adjusted_required_rate = required_progress_rate * conservative_factor
        
        time_critical = remaining_time < (self.task_duration * self.critical_threshold)
        
        if time_critical:
            return ClusterType.ON_DEMAND
        
        in_restart = (
            last_cluster_type != ClusterType.SPOT and 
            self.env.cluster_type == ClusterType.SPOT and
            (current_time - max(self.task_done_time) if self.task_done_time else 0) < self.restart_overhead
        )
        
        if in_restart:
            return ClusterType.SPOT
        
        if has_spot:
            spot_cost_efficiency = 0.97 / 3.06
            expected_spot_rate = spot_prob
            
            if expected_spot_rate >= adjusted_required_rate:
                return ClusterType.SPOT
            elif spot_prob > 0.6 and remaining_time > remaining_work * 1.5:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND if adjusted_required_rate > 0.8 else ClusterType.NONE
        else:
            if adjusted_required_rate > 0.9 or remaining_time < remaining_work * 1.2:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)