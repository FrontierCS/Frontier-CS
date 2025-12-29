import argparse
from typing import List, Optional
import math

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.spot_price = 0.97
        self.od_price = 3.06
        self.total_hours = 48
        self.deadline_hours = 70
        self.restart_hours = 0.2
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed_hours = self.env.elapsed_seconds / 3600
        remaining_hours = self.deadline - elapsed_hours
        done_work = sum(self.task_done_time) / 3600
        
        remaining_work = self.total_hours - done_work
        
        if remaining_work <= 0:
            return ClusterType.NONE
        
        if remaining_hours <= 0:
            return ClusterType.ON_DEMAND
        
        hours_per_step = self.env.gap_seconds / 3600
        
        # Critical threshold: if we're falling behind, switch to OD
        required_rate = remaining_work / remaining_hours
        
        # Estimate spot availability probability based on recent history
        # Use exponential moving average of spot availability
        if not hasattr(self, 'spot_availability_ema'):
            self.spot_availability_ema = 0.5
            self.spot_availability_samples = 0
            
        alpha = 0.1
        self.spot_availability_ema = (alpha * (1.0 if has_spot else 0.0) + 
                                     (1 - alpha) * self.spot_availability_ema)
        self.spot_availability_samples += 1
        
        # Calculate effective work rate with spot
        if self.spot_availability_samples < 10:
            spot_success_prob = 0.5
        else:
            spot_success_prob = self.spot_availability_ema
            
        effective_spot_rate = spot_success_prob * (1 - self.restart_hours / (1/spot_success_prob))
        
        # Calculate break-even point for spot usage
        # Consider both immediate and strategic costs
        time_margin = remaining_hours - remaining_work
        
        # If we're very behind, use OD
        if required_rate > 0.95:
            return ClusterType.ON_DEMAND
        
        # If spot is not available, decide between OD and NONE
        if not has_spot:
            # Use OD if we're falling behind
            if required_rate > 0.8:
                return ClusterType.ON_DEMAND
            # Otherwise pause
            return ClusterType.NONE
        
        # Spot is available
        # If we have plenty of time, use spot
        if time_margin > 10 and required_rate < 0.7:
            return ClusterType.SPOT
        
        # Calculate risk-adjusted cost
        spot_cost_per_work = self.spot_price / effective_spot_rate if effective_spot_rate > 0 else float('inf')
        od_cost_per_work = self.od_price
        
        # Use spot if it's cost-effective and we have some margin
        if spot_cost_per_work < od_cost_per_work * 0.7 and time_margin > 2:
            return ClusterType.SPOT
        
        # If we're in the final stretch, be conservative
        if remaining_hours < 5:
            # Use OD if behind schedule
            if required_rate > 0.85:
                return ClusterType.ON_DEMAND
            # Otherwise use spot if available
            return ClusterType.SPOT
        
        # Default: use spot if available and we're not critically behind
        if required_rate < 0.9:
            return ClusterType.SPOT
        
        return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)