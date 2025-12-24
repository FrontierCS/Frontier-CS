import argparse
import math

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "adaptive_slack"

    def __init__(self, args):
        super().__init__(args)
        self.spot_price = 0.97
        self.od_price = 3.06
        self.price_ratio = self.spot_price / self.od_price
        self.critical_threshold = 0
        self.conservative_threshold = 0
        self.state = "normal"
        self.spot_streak = 0
        self.last_spot_available = True

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        work_done = sum(end - start for start, end in self.task_done_time)
        work_left = self.task_duration - work_done
        
        time_left = self.deadline - elapsed
        slack = time_left - work_left
        
        if slack <= self.restart_overhead * 2:
            self.state = "critical"
        elif slack <= self.restart_overhead * 4:
            self.state = "conservative"
        else:
            self.state = "normal"
        
        if self.state == "critical":
            if has_spot and last_cluster_type == ClusterType.SPOT:
                self.spot_streak += 1
                if self.spot_streak >= 3:
                    return ClusterType.SPOT
            self.spot_streak = 0
            return ClusterType.ON_DEMAND
        
        elif self.state == "conservative":
            if not has_spot:
                return ClusterType.ON_DEMAND
                
            if last_cluster_type == ClusterType.SPOT:
                self.spot_streak += 1
                if self.spot_streak >= 2:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                self.spot_streak = 0
                return ClusterType.ON_DEMAND
        
        else:
            if not has_spot:
                self.spot_streak = 0
                return ClusterType.ON_DEMAND
            
            if last_cluster_type != ClusterType.SPOT:
                self.spot_streak = 0
                return ClusterType.SPOT
            
            self.spot_streak += 1
            
            if self.spot_streak >= 1:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
