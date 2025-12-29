import heapq
import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.buffer_hours = 3.0
        self.spot_history = []
        self.spot_availability_threshold = 0.3
        self.consecutive_spot_failures = 0
        self.max_consecutive_failures = 2
        self.last_decision = ClusterType.NONE
        self.restart_pending = False
        self.restart_timer = 0.0
        self.total_spot_time = 0.0
        self.total_od_time = 0.0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        deadline = self.deadline
        restart_overhead = self.restart_overhead
        
        remaining_work = self.task_duration - sum(self.task_done_time)
        time_left = deadline - elapsed
        
        if remaining_work <= 0:
            return ClusterType.NONE
            
        if self.restart_pending:
            self.restart_timer -= gap
            if self.restart_timer <= 0:
                self.restart_pending = False
            return ClusterType.NONE
        
        urgent = remaining_work > time_left - self.buffer_hours * 3600
        
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_spot_failures += 1
            if urgent:
                return ClusterType.ON_DEMAND
            self.restart_pending = True
            self.restart_timer = restart_overhead
            return ClusterType.NONE
        
        self.spot_history.append(has_spot)
        if len(self.spot_history) > 10:
            self.spot_history.pop(0)
        
        spot_reliability = sum(self.spot_history) / len(self.spot_history) if self.spot_history else 0
        
        if last_cluster_type == ClusterType.ON_DEMAND:
            self.consecutive_spot_failures = 0
            if not urgent and spot_reliability > self.spot_availability_threshold:
                if has_spot:
                    return ClusterType.SPOT
                return ClusterType.NONE
            return ClusterType.ON_DEMAND
        
        if last_cluster_type == ClusterType.SPOT:
            self.consecutive_spot_failures = 0
            if has_spot and not urgent:
                return ClusterType.SPOT
            if urgent:
                return ClusterType.ON_DEMAND
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.NONE
        
        if self.consecutive_spot_failures >= self.max_consecutive_failures:
            if urgent:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE
        
        if has_spot and spot_reliability > self.spot_availability_threshold:
            return ClusterType.SPOT
        
        if urgent:
            return ClusterType.ON_DEMAND
        
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)