import numpy as np
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.remaining_work = 0.0
        self.spot_availability = []
        self.spot_prices = []
        self.on_demand_prices = []
        self.step_duration = 0.0
        self.restart_penalty = 0.0
        self.deadline = 0.0
        self.current_overhead = 0.0
        self.last_decision = ClusterType.NONE
        self.spot_use_history = []
        self.predictions = []
        self.safety_margin = 1.2
        self.min_spot_ratio = 0.6
        
    def solve(self, spec_path: str) -> "Solution":
        return self
        
    def predict_spot_availability(self, steps_to_predict=100):
        """Simple prediction based on recent availability"""
        if len(self.spot_availability) < 10:
            return [True] * steps_to_predict
            
        window = min(50, len(self.spot_availability))
        recent = self.spot_availability[-window:]
        availability_rate = sum(recent) / len(recent)
        
        predictions = []
        for i in range(steps_to_predict):
            if i < 10:
                predictions.append(self.spot_availability[-1])
            else:
                predictions.append(np.random.random() < availability_rate * 0.9)
        return predictions
        
    def compute_min_time_needed(self, current_work, use_on_demand=False):
        """Compute minimum time needed to finish remaining work"""
        if use_on_demand:
            return current_work
        
        base_time = current_work
        if self.last_decision != ClusterType.SPOT and self.last_decision != ClusterType.NONE:
            base_time += self.restart_penalty
            
        return base_time * 1.1
        
    def calculate_urgency(self, time_left, work_left):
        """Calculate urgency level based on remaining time and work"""
        if work_left <= 0:
            return 0
            
        min_time_on_demand = self.compute_min_time_needed(work_left, True)
        min_time_spot = self.compute_min_time_needed(work_left, False)
        
        if time_left < min_time_on_demand:
            return 2.0
        elif time_left < min_time_spot * self.safety_margin:
            return 1.5
        elif time_left < min_time_spot * self.safety_margin * 1.5:
            return 1.0
        else:
            return 0.5
            
    def should_switch_to_ondemand(self, time_left, work_left, has_spot):
        """Determine if we should switch to on-demand"""
        if not has_spot:
            return True
            
        urgency = self.calculate_urgency(time_left, work_left)
        
        if urgency > 1.0:
            return True
            
        min_spot_time = self.compute_min_time_needed(work_left, False)
        if time_left < min_spot_time * 1.1:
            return True
            
        recent_spot_usage = sum(self.spot_use_history[-20:]) if len(self.spot_use_history) >= 20 else 0
        if recent_spot_usage / min(20, len(self.spot_use_history)) < self.min_spot_ratio:
            return False
            
        return False
        
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self.remaining_work = self.task_duration - sum(self.task_done_time)
        time_left = self.deadline - self.env.elapsed_seconds
        
        self.spot_availability.append(has_spot)
        if len(self.spot_availability) > 100:
            self.spot_availability.pop(0)
            
        if self.current_overhead > 0:
            self.current_overhead = max(0, self.current_overhead - self.env.gap_seconds)
            
        if self.current_overhead > 0:
            self.spot_use_history.append(0)
            self.last_decision = ClusterType.NONE
            return ClusterType.NONE
            
        if self.remaining_work <= 0:
            self.spot_use_history.append(0)
            self.last_decision = ClusterType.NONE
            return ClusterType.NONE
            
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.current_overhead = self.restart_overhead
            self.spot_use_history.append(0)
            self.last_decision = ClusterType.NONE
            return ClusterType.NONE
            
        use_ondemand = self.should_switch_to_ondemand(time_left, self.remaining_work, has_spot)
        
        if use_ondemand:
            if last_cluster_type != ClusterType.ON_DEMAND:
                self.current_overhead = self.restart_overhead
                self.spot_use_history.append(0)
                self.last_decision = ClusterType.NONE
                return ClusterType.NONE
            else:
                self.spot_use_history.append(0)
                self.last_decision = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND
        else:
            if has_spot:
                self.spot_use_history.append(1)
                self.last_decision = ClusterType.SPOT
                return ClusterType.SPOT
            else:
                self.spot_use_history.append(0)
                self.last_decision = ClusterType.NONE
                return ClusterType.NONE
                
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
