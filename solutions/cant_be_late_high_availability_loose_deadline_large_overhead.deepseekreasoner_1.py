import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.remaining_work = 0.0
        self.spot_history = []
        self.consecutive_spot_uptime = 0
        self.time_since_last_restart = 0
        self.spot_unavailable_counter = 0
        self.conservative_mode = False
        self.urgent_mode = False
        self.last_decision = ClusterType.NONE
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def _calculate_required_progress_rate(self, time_remaining, work_remaining, overhead_buffer=0.0):
        if time_remaining <= 0:
            return float('inf')
        return max(0.0, work_remaining / (time_remaining - overhead_buffer))
    
    def _should_use_ondemand_emergency(self, time_remaining, work_remaining):
        min_time_with_overhead = work_remaining + self.restart_overhead
        safety_factor = 1.2
        return time_remaining < min_time_with_overhead * safety_factor
    
    def _get_spot_reliability_estimate(self):
        if len(self.spot_history) < 10:
            return 0.7
        recent_history = self.spot_history[-10:]
        available_count = sum(1 for available in recent_history if available)
        return available_count / len(recent_history)
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self.spot_history.append(has_spot)
        if len(self.spot_history) > 100:
            self.spot_history.pop(0)
        
        current_time = self.env.elapsed_seconds
        time_remaining = self.deadline - current_time
        
        if not hasattr(self, 'initial_work_remaining'):
            self.initial_work_remaining = self.task_duration
            self.remaining_work = self.task_duration
        
        total_done = sum(self.task_done_time)
        self.remaining_work = max(0.0, self.task_duration - total_done)
        
        if self.remaining_work <= 0:
            return ClusterType.NONE
        
        if time_remaining <= 0:
            return ClusterType.ON_DEMAND
        
        if last_cluster_type == ClusterType.SPOT:
            if has_spot:
                self.consecutive_spot_uptime += self.env.gap_seconds
                self.time_since_last_restart += self.env.gap_seconds
                self.spot_unavailable_counter = 0
            else:
                self.spot_unavailable_counter += 1
                self.consecutive_spot_uptime = 0
        elif last_cluster_type == ClusterType.ON_DEMAND:
            self.time_since_last_restart += self.env.gap_seconds
            self.spot_unavailable_counter = 0
        else:
            self.time_since_last_restart += self.env.gap_seconds
        
        if self.time_since_last_restart > 3600:
            self.time_since_last_restart = 3600
        
        required_rate = self._calculate_required_progress_rate(
            time_remaining, 
            self.remaining_work,
            overhead_buffer=self.restart_overhead * 2
        )
        
        emergency = self._should_use_ondemand_emergency(time_remaining, self.remaining_work)
        
        if emergency:
            return ClusterType.ON_DEMAND
        
        spot_reliability = self._get_spot_reliability_estimate()
        
        time_until_deadline_ratio = time_remaining / (self.deadline * 0.5)
        work_ratio = self.remaining_work / self.initial_work_remaining
        
        if time_until_deadline_ratio < 0.3 or work_ratio > 0.8:
            self.conservative_mode = True
        else:
            self.conservative_mode = False
            
        if time_until_deadline_ratio < 0.15 or work_ratio > 0.95:
            self.urgent_mode = True
        else:
            self.urgent_mode = False
        
        if self.urgent_mode:
            if has_spot and spot_reliability > 0.8 and self.consecutive_spot_uptime > 1800:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        if self.conservative_mode:
            if has_spot and spot_reliability > 0.7 and self.consecutive_spot_uptime > 900:
                return ClusterType.SPOT
            if not has_spot and time_remaining > self.remaining_work * 1.5:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND
        
        if has_spot:
            if spot_reliability < 0.5 and self.spot_unavailable_counter > 3:
                if time_remaining > self.remaining_work * 2:
                    return ClusterType.NONE
                return ClusterType.ON_DEMAND
            
            if self.time_since_last_restart < self.restart_overhead * 0.5:
                if last_cluster_type == ClusterType.NONE:
                    return ClusterType.NONE
            
            time_advantage = time_remaining - self.remaining_work
            risk_tolerance = min(1.0, time_advantage / (self.restart_overhead * 5))
            
            if spot_reliability > 0.6 or risk_tolerance > 0.3:
                if self.consecutive_spot_uptime > 300 or self.time_since_last_restart > 600:
                    return ClusterType.SPOT
            
            if last_cluster_type == ClusterType.SPOT and self.consecutive_spot_uptime > 60:
                return ClusterType.SPOT
            
            if spot_reliability > 0.4 and risk_tolerance > 0.5:
                return ClusterType.SPOT
            
            if time_remaining > self.remaining_work * 3:
                return ClusterType.SPOT
        
        if not has_spot:
            if time_remaining > self.remaining_work * 1.8:
                if self.spot_unavailable_counter < 5:
                    return ClusterType.NONE
            
            if time_remaining > self.remaining_work * 1.3 and spot_reliability > 0.4:
                return ClusterType.NONE
        
        return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
