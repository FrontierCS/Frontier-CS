import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.spot_price = 0.97
        self.ondemand_price = 3.06
        self.spot_ratio = self.spot_price / self.ondemand_price
        self.overhead_hours = 0.05
        self.task_hours = 48
        self.deadline_hours = 52
        self.slack_hours = 4
        self.overhead_budget = None
        self.last_availability = None
        self.spot_unavailable_count = 0
        self.consecutive_spot_failures = 0
        self.max_consecutive_failures = 5
        self.panic_threshold = None
        self.initialized = False
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def _initialize_state(self):
        if self.initialized:
            return
            
        self.overhead_budget = self.slack_hours
        hours_elapsed = self.env.elapsed_seconds / 3600
        remaining_hours = self.deadline_hours - hours_elapsed
        
        remaining_work = self.task_hours - self._get_total_work_done()
        
        self.panic_threshold = remaining_work * 1.5 + self.overhead_hours
        
        if remaining_hours < self.panic_threshold:
            self.overhead_budget = max(0, remaining_hours - remaining_work)
        else:
            self.overhead_budget = min(self.slack_hours, remaining_hours - remaining_work)
        
        self.initialized = True
    
    def _get_total_work_done(self):
        total = 0
        for start, end in self.task_done_time:
            total += (end - start)
        return total / 3600
    
    def _get_remaining_work(self):
        done = self._get_total_work_done()
        return max(0, self.task_hours - done)
    
    def _get_time_left(self):
        hours_elapsed = self.env.elapsed_seconds / 3600
        return max(0, self.deadline_hours - hours_elapsed)
    
    def _should_panic(self, remaining_work, time_left):
        hours_elapsed = self.env.elapsed_seconds / 3600
        
        if hours_elapsed > self.deadline_hours * 0.8:
            buffer_needed = remaining_work + self.overhead_hours
            if time_left < buffer_needed:
                return True
        
        buffer_ratio = time_left / remaining_work if remaining_work > 0 else float('inf')
        return buffer_ratio < 1.2
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_state()
        
        if not has_spot:
            self.spot_unavailable_count += 1
            self.consecutive_spot_failures += 1
        else:
            self.consecutive_spot_failures = 0
        
        self.last_availability = has_spot
        
        remaining_work = self._get_remaining_work()
        time_left = self._get_time_left()
        
        if remaining_work <= 0:
            return ClusterType.NONE
            
        if time_left <= 0:
            return ClusterType.NONE
        
        hours_elapsed = self.env.elapsed_seconds / 3600
        
        if self._should_panic(remaining_work, time_left):
            return ClusterType.ON_DEMAND
        
        step_hours = self.env.gap_seconds / 3600
        can_afford_overhead = self.overhead_budget >= self.overhead_hours
        
        if has_spot and can_afford_overhead:
            if self.consecutive_spot_failures >= self.max_consecutive_failures:
                if remaining_work > time_left * 0.9:
                    return ClusterType.ON_DEMAND
            
            spot_probability = min(1.0, (time_left - remaining_work) / self.slack_hours)
            
            if spot_probability > 0.3 or remaining_work > time_left * 0.7:
                risk_factor = remaining_work / time_left
                
                if risk_factor < 0.8:
                    self.overhead_budget -= step_hours
                    return ClusterType.SPOT
                else:
                    if has_spot and hours_elapsed < self.deadline_hours * 0.6:
                        self.overhead_budget -= step_hours
                        return ClusterType.SPOT
        
        if remaining_work > time_left:
            return ClusterType.ON_DEMAND
        
        if not has_spot and remaining_work < time_left * 0.9:
            return ClusterType.NONE
        
        if hours_elapsed > self.deadline_hours * 0.9:
            return ClusterType.ON_DEMAND
        
        if has_spot and self.overhead_budget > self.overhead_hours * 2:
            self.overhead_budget -= step_hours
            return ClusterType.SPOT
        
        return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
