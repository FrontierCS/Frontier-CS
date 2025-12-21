import sys
import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__(args)
        self.spot_cost = 0.97 / 3600  # $/second
        self.od_cost = 3.06 / 3600  # $/second
        self.restart_penalty = 0.20 * 3600  # seconds
        self.slack = 4 * 3600  # seconds
        
    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_time = self.env.elapsed_seconds
        time_left = self.deadline - current_time
        completed = sum(self.task_done_time)
        remaining = self.task_duration - completed
        
        if remaining <= 0:
            return ClusterType.NONE
            
        if not has_spot:
            if self._should_use_od(current_time, remaining, time_left):
                return ClusterType.ON_DEMAND
            return ClusterType.NONE
        
        # Calculate safe thresholds
        time_needed = remaining + (0 if last_cluster_type == ClusterType.SPOT else self.restart_overhead)
        
        # Emergency mode - must use OD to finish
        if time_needed > time_left - self.restart_overhead:
            return ClusterType.ON_DEMAND
            
        # Calculate efficiency score
        spot_score = self._calculate_spot_score(current_time, time_left, remaining)
        od_score = self._calculate_od_score(time_left, remaining)
        
        if spot_score > od_score:
            return ClusterType.SPOT
        elif od_score > 0:
            return ClusterType.ON_DEMAND
        return ClusterType.NONE

    def _should_use_od(self, current_time, remaining, time_left):
        # Use OD if we're running out of time or have enough budget
        min_time_needed = remaining + (0 if self.env.cluster_type == ClusterType.ON_DEMAND else self.restart_overhead)
        if min_time_needed >= time_left - self.restart_overhead:
            return True
            
        # Calculate progress percentage
        progress = (self.task_duration - remaining) / self.task_duration
        time_percentage = current_time / self.deadline
        
        # Use OD if falling behind schedule
        if progress < time_percentage * 0.8:
            return True
            
        return False

    def _calculate_spot_score(self, current_time, time_left, remaining):
        if not hasattr(self, '_spot_history'):
            self._spot_history = []
            
        # Track spot availability
        self._spot_history.append(1 if hasattr(self, 'last_has_spot') and self.last_has_spot else 0)
        if len(self._spot_history) > 100:
            self._spot_history.pop(0)
            
        spot_availability = sum(self._spot_history) / len(self._spot_history) if self._spot_history else 0.5
        self.last_has_spot = True
        
        # Calculate risk factor
        time_needed = remaining + self.restart_overhead
        risk_factor = time_needed / (time_left + 1e-6)
        
        # Score based on availability and risk
        base_score = self.od_cost / (self.spot_cost + 1e-6) - 1  # Cost advantage
        availability_score = spot_availability * 2
        risk_penalty = risk_factor * 5
        
        return max(0, base_score + availability_score - risk_penalty)

    def _calculate_od_score(self, time_left, remaining):
        time_needed = remaining + (0 if self.env.cluster_type == ClusterType.ON_DEMAND else self.restart_overhead)
        
        # OD is valuable when time is tight
        urgency = 1 - (time_left - time_needed) / self.slack
        urgency = max(0, min(1, urgency))
        
        # Progress-based urgency
        progress = (self.task_duration - remaining) / self.task_duration
        expected_progress = self.env.elapsed_seconds / self.deadline
        progress_urgency = max(0, expected_progress - progress)
        
        return urgency + progress_urgency * 2

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
