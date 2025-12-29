import json
import math
from typing import List, Tuple, Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_threshold_scheduler"

    def __init__(self, args=None):
        super().__init__(args)
        self.spec = None
        self.spot_price = 0.97
        self.ondemand_price = 3.06
        self.price_ratio = self.ondemand_price / self.spot_price
        self.restart_penalty_factor = 2.0
        self.conservative_slack = 4.0 * 3600
        self.emergency_threshold = 0.15
        self.max_consecutive_spot_failures = 10
        self.consecutive_spot_failures = 0
        self.spot_history = []
        self.work_progress = 0.0
        self.work_rate = 0.0
        self.last_decision = None
        self.in_restart = False
        self.restart_remaining = 0.0
        
    def solve(self, spec_path: str) -> "Solution":
        try:
            with open(spec_path, 'r') as f:
                self.spec = json.load(f)
        except:
            pass
        return self

    def _calculate_progress_rate(self) -> float:
        if not self.task_done_time:
            return 0.0
        
        total_work = 0.0
        total_time = 0.0
        
        for start, end in self.task_done_time:
            total_work += (end - start)
            total_time += (end - start)
        
        if total_time == 0:
            return 0.0
        
        return total_work / total_time

    def _calculate_remaining_work(self) -> float:
        total_done = 0.0
        for start, end in self.task_done_time:
            total_done += (end - start)
        return max(0.0, self.task_duration - total_done)

    def _get_time_to_deadline(self) -> float:
        return max(0.0, self.deadline - self.env.elapsed_seconds)

    def _get_required_work_rate(self) -> float:
        remaining_work = self._calculate_remaining_work()
        time_to_deadline = self._get_time_to_deadline()
        
        if time_to_deadline <= 0:
            return float('inf')
        
        return remaining_work / time_to_deadline

    def _should_use_ondemand(self, last_cluster_type: ClusterType, 
                             has_spot: bool) -> bool:
        remaining_work = self._calculate_remaining_work()
        time_to_deadline = self._get_time_to_deadline()
        
        if time_to_deadline <= 0:
            return True
            
        required_rate = self._get_required_work_rate()
        
        emergency_condition = (required_rate > 1.0 - self.emergency_threshold)
        
        if emergency_condition:
            return True
        
        if self.consecutive_spot_failures > self.max_consecutive_spot_failures:
            return True
        
        if last_cluster_type == ClusterType.NONE:
            time_needed = remaining_work + self.restart_overhead
            if time_needed > time_to_deadline - self.conservative_slack:
                return True
        
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            time_needed = remaining_work + self.restart_overhead
            if time_needed > time_to_deadline - self.conservative_slack:
                return True
        
        return False

    def _update_restart_state(self, last_cluster_type: ClusterType,
                             next_cluster_type: ClusterType) -> None:
        if (last_cluster_type == ClusterType.NONE and 
            next_cluster_type != ClusterType.NONE):
            self.in_restart = True
            self.restart_remaining = self.restart_overhead
        elif (last_cluster_type == ClusterType.SPOT and 
              next_cluster_type == ClusterType.ON_DEMAND):
            self.in_restart = True
            self.restart_remaining = self.restart_overhead
        elif (last_cluster_type == ClusterType.ON_DEMAND and 
              next_cluster_type == ClusterType.SPOT):
            self.in_restart = True
            self.restart_remaining = self.restart_overhead
        elif next_cluster_type == ClusterType.NONE:
            self.in_restart = False
            self.restart_remaining = 0.0
        elif self.in_restart and self.restart_remaining > 0:
            self.restart_remaining -= self.env.gap_seconds
            if self.restart_remaining <= 0:
                self.in_restart = False
                self.restart_remaining = 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining_work = self._calculate_remaining_work()
        time_to_deadline = self._get_time_to_deadline()
        
        if remaining_work <= 0:
            return ClusterType.NONE
            
        if time_to_deadline <= 0:
            return ClusterType.ON_DEMAND
        
        self._update_restart_state(last_cluster_type, last_cluster_type)
        
        if self._should_use_ondemand(last_cluster_type, has_spot):
            self.consecutive_spot_failures = 0
            return ClusterType.ON_DEMAND
        
        if has_spot:
            if last_cluster_type == ClusterType.SPOT:
                self.consecutive_spot_failures = 0
                return ClusterType.SPOT
            elif last_cluster_type == ClusterType.ON_DEMAND:
                if remaining_work / time_to_deadline > 0.8:
                    return ClusterType.ON_DEMAND
                else:
                    self.consecutive_spot_failures = 0
                    return ClusterType.SPOT
            else:
                self.consecutive_spot_failures = 0
                return ClusterType.SPOT
        else:
            self.consecutive_spot_failures += 1
            
            if last_cluster_type == ClusterType.SPOT:
                if remaining_work / time_to_deadline > 0.7:
                    return ClusterType.ON_DEMAND
                else:
                    return ClusterType.NONE
            else:
                if remaining_work / time_to_deadline > 0.6:
                    return ClusterType.ON_DEMAND
                else:
                    return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)