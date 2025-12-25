import numpy as np
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def solve(self, spec_path: str) -> "Solution":
        self.work_done = 0.0
        self.spot_available_history = []
        self.decision_history = []
        self.consecutive_spot_failures = 0
        self.max_consecutive_failures = 0
        self.switch_to_od_threshold = 0
        self.safety_margin = 0.1
        self.last_work_time = 0.0
        self.pause_count = 0
        self.od_usage = 0
        
        return self
    
    def _compute_progress_rate(self):
        if len(self.decision_history) == 0:
            return 0.0
        
        work_periods = 0
        for i, decision in enumerate(self.decision_history[-100:]):
            if decision in [ClusterType.SPOT, ClusterType.ON_DEMAND]:
                work_periods += 1
        
        return work_periods / min(100, len(self.decision_history))
    
    def _estimate_remaining_time(self, remaining_work):
        progress_rate = self._compute_progress_rate()
        if progress_rate > 0:
            estimated_steps = remaining_work / (self.env.gap_seconds * progress_rate)
        else:
            estimated_steps = remaining_work / self.env.gap_seconds
        
        return estimated_steps * self.env.gap_seconds
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_time = self.env.elapsed_seconds
        time_left = self.deadline - current_time
        
        remaining_work = self.task_duration - sum(self.task_done_time)
        
        if remaining_work <= 0:
            return ClusterType.NONE
        
        self.spot_available_history.append(has_spot)
        if len(self.spot_available_history) > 100:
            self.spot_available_history.pop(0)
        
        spot_availability = np.mean(self.spot_available_history) if self.spot_available_history else 0.5
        
        if has_spot:
            self.consecutive_spot_failures = 0
        else:
            self.consecutive_spot_failures += 1
            self.max_consecutive_failures = max(self.max_consecutive_failures, 
                                              self.consecutive_spot_failures)
        
        if self.switch_to_od_threshold == 0 and len(self.spot_available_history) >= 20:
            self.switch_to_od_threshold = max(3, int(self.max_consecutive_failures * 0.8))
        
        estimated_remaining_time = self._estimate_remaining_time(remaining_work)
        
        critical_phase = time_left < estimated_remaining_time * (1.0 + self.safety_margin)
        
        if critical_phase:
            self.od_usage += 1
            
        use_od = (
            critical_phase or
            (not has_spot and self.consecutive_spot_failures >= self.switch_to_od_threshold) or
            (remaining_work / self.env.gap_seconds > time_left / self.env.gap_seconds - 5) or
            (self.od_usage < 5 and time_left < 3600)
        )
        
        if use_od:
            decision = ClusterType.ON_DEMAND
        elif has_spot:
            if last_cluster_type == ClusterType.NONE:
                self.pause_count += 1
            
            if self.pause_count > 2 and not critical_phase:
                decision = ClusterType.SPOT
            else:
                decision = ClusterType.SPOT
        else:
            if time_left > estimated_remaining_time * 1.2 and not critical_phase:
                decision = ClusterType.NONE
            else:
                decision = ClusterType.ON_DEMAND
        
        self.decision_history.append(decision)
        if len(self.decision_history) > 1000:
            self.decision_history.pop(0)
        
        return decision
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)