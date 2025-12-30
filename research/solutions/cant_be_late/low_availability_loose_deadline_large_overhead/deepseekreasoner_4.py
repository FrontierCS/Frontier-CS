import argparse
import math
from typing import List, Tuple, Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_hedging"
    
    def __init__(self, args=None):
        super().__init__(args)
        self.safety_margin = 0
        self.conservative_threshold = 0
        self.use_aggressive_spot = False
        self.last_decision = ClusterType.NONE
        self.consecutive_spot_failures = 0
        self.spot_attempts = 0
        self.total_steps = 0
        
    def solve(self, spec_path: str) -> "Solution":
        try:
            with open(spec_path, 'r') as f:
                content = f.read().strip()
                if content:
                    params = eval(content)
                    self.safety_margin = params.get('safety_margin', 2.0)
                    self.conservative_threshold = params.get('conservative_threshold', 0.3)
                    self.use_aggressive_spot = params.get('use_aggressive_spot', False)
        except:
            self.safety_margin = 2.0
            self.conservative_threshold = 0.3
            self.use_aggressive_spot = False
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self.total_steps += 1
        
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_spot_failures += 1
        else:
            self.consecutive_spot_failures = max(0, self.consecutive_spot_failures - 1)
        
        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE
        
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        gap = self.env.gap_seconds
        
        if time_left <= 0:
            return ClusterType.NONE
        
        required_steps = math.ceil(remaining_work / gap)
        available_steps = math.ceil(time_left / gap)
        
        if required_steps > available_steps:
            return ClusterType.ON_DEMAND
        
        if self.consecutive_spot_failures >= 3:
            safety_buffer = self.restart_overhead * 2
        else:
            safety_buffer = self.restart_overhead
        
        critical_ratio = required_steps / available_steps if available_steps > 0 else 1.0
        
        if self.use_aggressive_spot:
            if has_spot:
                self.spot_attempts += 1
                spot_success_rate = 1.0 - (self.consecutive_spot_failures / max(1, self.spot_attempts))
                
                if spot_success_rate > 0.5 or critical_ratio < 0.5:
                    return ClusterType.SPOT
                elif critical_ratio < 0.7:
                    return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND
                else:
                    time_needed_od = remaining_work
                    time_needed_spot = remaining_work + (safety_buffer * (remaining_work / (gap * 10)))
                    
                    if time_left > time_needed_spot * 1.2:
                        return ClusterType.SPOT
                    elif time_left > time_needed_od * 1.1:
                        return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND
                    else:
                        return ClusterType.ON_DEMAND
            else:
                if critical_ratio > self.conservative_threshold:
                    return ClusterType.ON_DEMAND
                return ClusterType.NONE
        else:
            if critical_ratio > self.conservative_threshold:
                return ClusterType.ON_DEMAND
            
            required_time_with_buffer = remaining_work + safety_buffer
            if time_left < required_time_with_buffer * self.safety_margin:
                return ClusterType.ON_DEMAND
            
            if has_spot:
                recent_spot_available = self._estimate_spot_availability()
                if recent_spot_available > 0.6 or critical_ratio < 0.2:
                    return ClusterType.SPOT
                elif critical_ratio < 0.4:
                    return ClusterType.SPOT
                else:
                    return ClusterType.NONE
            else:
                if critical_ratio < 0.1:
                    return ClusterType.ON_DEMAND
                return ClusterType.NONE
    
    def _estimate_spot_availability(self) -> float:
        if self.total_steps < 10:
            return 0.7
        return 0.5
    
    @classmethod
    def _from_args(cls, parser):
        parser.add_argument('--safety_margin', type=float, default=2.0)
        parser.add_argument('--conservative_threshold', type=float, default=0.3)
        parser.add_argument('--use_aggressive_spot', action='store_true')
        args, _ = parser.parse_known_args()
        return cls(args)