import json
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType
from typing import List, Tuple
import math


class Solution(Strategy):
    NAME = "adaptive_deadline_aware"

    def __init__(self, args):
        super().__init__(args)
        self.safety_margin = None
        self.aggressiveness = None
        self.restart_penalty = None
        self.remaining_work = None
        self.time_left = None
        self.spot_unavailable_streak = 0
        self.consecutive_spot_failures = 0
        self.spot_availability_history = []
        self.phase = "aggressive"  # aggressive, cautious, emergency
        
    def solve(self, spec_path: str) -> "Solution":
        try:
            with open(spec_path, 'r') as f:
                config = json.load(f)
                self.safety_margin = config.get("safety_margin", 1.2)
                self.aggressiveness = config.get("aggressiveness", 0.7)
        except:
            self.safety_margin = 1.2
            self.aggressiveness = 0.7
            
        return self
    
    def _calculate_metrics(self):
        """Calculate current metrics for decision making"""
        self.remaining_work = self.task_duration - sum(self.task_done_time)
        self.time_left = self.deadline - self.env.elapsed_seconds
        
        # Calculate required completion rate
        if self.time_left > 0:
            self.required_rate = self.remaining_work / self.time_left
        else:
            self.required_rate = float('inf')
            
        # Calculate slack
        self.slack = self.time_left - self.remaining_work
        
        # Update spot availability history
        current_has_spot = self.env.cluster_type == ClusterType.SPOT
        self.spot_availability_history.append(current_has_spot)
        if len(self.spot_availability_history) > 100:
            self.spot_availability_history.pop(0)
    
    def _get_spot_availability_probability(self) -> float:
        """Estimate spot availability based on recent history"""
        if not self.spot_availability_history:
            return 0.5
        
        available_count = sum(self.spot_availability_history)
        return available_count / len(self.spot_availability_history)
    
    def _should_use_spot(self, has_spot: bool) -> bool:
        """Determine if spot should be used based on current state"""
        if not has_spot:
            return False
            
        # Calculate expected completion time with spot
        spot_prob = self._get_spot_availability_probability()
        expected_spot_rate = spot_prob * (1 - 0.1)  # Penalty for potential preemptions
        
        # Emergency mode - switch to on-demand if we're critically behind
        if self.slack < self.restart_overhead * 2:
            return False
            
        # If we're ahead of schedule, be more aggressive with spot
        if self.slack > self.restart_overhead * 4:
            return True
            
        # If spot has been reliable recently, use it
        if spot_prob > 0.6 and self.consecutive_spot_failures < 3:
            return True
            
        # If we need to catch up, spot might be too risky
        if self.required_rate > 1.0:
            return spot_prob > 0.8
            
        return spot_prob > 0.4
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update restart penalty (convert hours to seconds)
        self.restart_penalty = self.restart_overhead * 3600
        
        # Update metrics
        self._calculate_metrics()
        
        # Track spot availability streaks
        if has_spot:
            self.spot_unavailable_streak = 0
        else:
            self.spot_unavailable_streak += 1
            
        # Track consecutive spot failures
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_spot_failures += 1
        elif has_spot and self.consecutive_spot_failures > 0:
            self.consecutive_spot_failures = max(0, self.consecutive_spot_failures - 1)
        
        # Emergency check - must finish
        if self.time_left <= self.remaining_work + self.restart_penalty:
            return ClusterType.ON_DEMAND
        
        # If no work left, do nothing
        if self.remaining_work <= 0:
            return ClusterType.NONE
        
        # Determine strategy based on phase
        if self.slack < self.restart_penalty * 2:
            self.phase = "emergency"
        elif self.slack < self.restart_penalty * 4:
            self.phase = "cautious"
        else:
            self.phase = "aggressive"
        
        # Make decision based on phase
        if self.phase == "emergency":
            return ClusterType.ON_DEMAND
            
        elif self.phase == "cautious":
            if has_spot and self._get_spot_availability_probability() > 0.7:
                if self.consecutive_spot_failures < 2:
                    return ClusterType.SPOT
            return ClusterType.ON_DEMAND
            
        else:  # aggressive phase
            if has_spot:
                if self.spot_unavailable_streak < 5 or self._get_spot_availability_probability() > 0.5:
                    return ClusterType.SPOT
                elif self.slack > self.restart_penalty * 6:
                    return ClusterType.NONE  # Wait for spot
                else:
                    return ClusterType.ON_DEMAND
            else:
                # Spot unavailable
                if self.slack > self.restart_penalty * 8:
                    return ClusterType.NONE  # Wait for spot
                else:
                    return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)