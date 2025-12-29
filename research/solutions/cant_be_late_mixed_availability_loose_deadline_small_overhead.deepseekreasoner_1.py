import argparse
import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_deadline_aware"

    def __init__(self, args):
        super().__init__(args)
        self.spec = None
        self.spot_price = None
        self.od_price = None
        self.initialized = False
        self.spot_availability_est = 0.5
        self.consecutive_none = 0
        self.last_decision = None
        self.in_overhead = False
        self.overhead_remaining = 0.0
        
    def _initialize_from_spec(self):
        if self.initialized:
            return
            
        try:
            import json
            with open(self.spec, 'r') as f:
                config = json.load(f)
                self.spot_price = config.get('spot_price', 0.97)
                self.od_price = config.get('od_price', 3.06)
                self.spot_availability_est = config.get('avg_availability', 0.5)
        except:
            self.spot_price = 0.97
            self.od_price = 3.06
            self.spot_availability_est = 0.5
            
        self.initialized = True
    
    def solve(self, spec_path: str) -> "Solution":
        self.spec = spec_path
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self.initialized:
            self._initialize_from_spec()
        
        current_time = self.env.elapsed_seconds
        time_step = self.env.gap_seconds
        work_done = sum(self.task_done_time) if self.task_done_time else 0
        work_remaining = self.task_duration - work_done
        deadline = self.deadline
        overhead = self.restart_overhead
        
        time_remaining = deadline - current_time
        
        if work_remaining <= 0:
            return ClusterType.NONE
        
        if self.in_overhead:
            self.overhead_remaining -= time_step
            if self.overhead_remaining <= 0:
                self.in_overhead = False
                self.overhead_remaining = 0
            return ClusterType.NONE
        
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.in_overhead = True
            self.overhead_remaining = overhead
            return ClusterType.NONE
        
        if has_spot:
            if self._should_switch_to_od(last_cluster_type, work_remaining, time_remaining, time_step):
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.SPOT
        else:
            if self._should_use_od_when_no_spot(work_remaining, time_remaining, time_step):
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE
    
    def _should_switch_to_od(self, last_type, work_remaining, time_remaining, time_step):
        if last_type == ClusterType.ON_DEMAND:
            return True
            
        if work_remaining <= 0:
            return False
            
        if time_remaining <= 0:
            return False
            
        time_needed_if_od = work_remaining
        if time_needed_if_od >= time_remaining:
            return True
            
        time_needed_if_spot = work_remaining + (overhead_cost := self._estimate_overhead_cost(time_remaining))
        
        safety_margin = max(2.0, work_remaining * 0.1)
        
        if time_needed_if_spot + safety_margin >= time_remaining:
            return True
            
        progress_rate_needed = work_remaining / time_remaining
        spot_success_rate = self.spot_availability_est
        
        if spot_success_rate < 0.5 and progress_rate_needed > 0.8:
            return True
            
        return False
    
    def _should_use_od_when_no_spot(self, work_remaining, time_remaining, time_step):
        if work_remaining <= 0:
            return False
            
        if time_remaining <= 0:
            return True
            
        time_needed_if_od = work_remaining
        
        if time_needed_if_od >= time_remaining:
            return True
            
        if self.consecutive_none > 3:
            return True
            
        progress_rate_needed = work_remaining / time_remaining
        
        if progress_rate_needed > 0.9:
            return True
            
        if time_remaining < work_remaining * 1.2:
            return True
            
        return False
    
    def _estimate_overhead_cost(self, time_remaining):
        total_overhead = 0
        remaining_time = time_remaining
        avg_spot_uptime = 3600.0
        
        while remaining_time > 0 and avg_spot_uptime > 0:
            expected_interruptions = remaining_time / avg_spot_uptime
            total_overhead += expected_interruptions * self.restart_overhead
            remaining_time = max(0, remaining_time - avg_spot_uptime)
            
        return total_overhead * 0.7
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)