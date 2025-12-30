import math
import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_safety_margin"

    def __init__(self, args):
        super().__init__(args)
        self.safety_margin = None
        self.initial_spot_availability = None
        self.spot_reliability = None
        self.restart_count = 0
        self.spot_runtime = 0
        self.last_spot_available = None
        self.consecutive_spot_blocks = 0
        self.max_consecutive_spot_blocks = 0
        self.total_steps = 0
        self.spot_available_steps = 0

    def solve(self, spec_path: str) -> "Solution":
        self.safety_margin = 0.15 * (self.deadline - self.task_duration)
        self.restart_count = 0
        self.spot_runtime = 0
        self.last_spot_available = None
        self.consecutive_spot_blocks = 0
        self.max_consecutive_spot_blocks = 0
        self.total_steps = 0
        self.spot_available_steps = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self.total_steps += 1
        if has_spot:
            self.spot_available_steps += 1
        
        current_time = self.env.elapsed_seconds
        time_remaining = self.deadline - current_time
        
        completed_work = sum(self.task_done_time)
        work_remaining = self.task_duration - completed_work
        
        if work_remaining <= 0:
            return ClusterType.NONE
        
        if time_remaining <= 0:
            return ClusterType.ON_DEMAND
        
        if has_spot:
            spot_price = 0.97
            ondemand_price = 3.06
            price_ratio = spot_price / ondemand_price
            
            work_rate = self.env.gap_seconds
            if last_cluster_type == ClusterType.SPOT:
                work_rate = self.env.gap_seconds
            
            min_time_needed = work_remaining
            conservative_min_time = min_time_needed * 1.1
            
            if last_cluster_type != ClusterType.SPOT and last_cluster_type != ClusterType.NONE:
                conservative_min_time += self.restart_overhead
            
            safety_adjusted_time = conservative_min_time + self.safety_margin
            
            if time_remaining > safety_adjusted_time:
                self.spot_runtime += 1
                if self.last_spot_available is False:
                    self.consecutive_spot_blocks += 1
                    self.max_consecutive_spot_blocks = max(
                        self.max_consecutive_spot_blocks, 
                        self.consecutive_spot_blocks
                    )
                self.last_spot_available = True
                return ClusterType.SPOT
            else:
                self.last_spot_available = False
                self.consecutive_spot_blocks = 0
                return ClusterType.ON_DEMAND
        else:
            work_rate = self.env.gap_seconds if last_cluster_type == ClusterType.ON_DEMAND else 0
            
            min_time_needed = work_remaining
            if last_cluster_type != ClusterType.ON_DEMAND:
                min_time_needed += self.restart_overhead if last_cluster_type == ClusterType.SPOT else 0
            
            time_critical = work_remaining * 1.2 > time_remaining
            
            if time_critical or work_remaining <= 2 * self.env.gap_seconds:
                self.last_spot_available = False
                return ClusterType.ON_DEMAND
            
            spot_availability = self.spot_available_steps / self.total_steps if self.total_steps > 0 else 0.5
            
            if spot_availability > 0.3 and time_remaining > work_remaining * 1.5:
                self.last_spot_available = False
                return ClusterType.NONE
            else:
                self.last_spot_available = False
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)