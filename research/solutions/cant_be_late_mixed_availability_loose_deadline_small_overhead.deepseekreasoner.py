import os
import json
import math
from typing import Dict, List, Tuple, Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "cant_be_late_optimized"
    
    def __init__(self, args):
        super().__init__(args)
        self.config = {}
        self.spot_history = []
        self.last_decision = ClusterType.NONE
        self.consecutive_spot = 0
        self.spot_availability_rate = 0.0
        self.remaining_time_at_start = 0.0
        self.work_done = 0.0
        self.spot_runs = []
        
    def solve(self, spec_path: str) -> "Solution":
        if os.path.exists(spec_path):
            try:
                with open(spec_path, 'r') as f:
                    self.config = json.load(f)
            except:
                self.config = {}
        return self
    
    def _get_aggressiveness_factor(self) -> float:
        """Calculate how aggressive we should be with spot based on remaining time."""
        remaining_time = self.deadline - self.env.elapsed_seconds
        total_work_needed = self.task_duration - sum(self.task_done_time)
        
        if remaining_time <= 0 or total_work_needed <= 0:
            return 0.0
            
        # Calculate how much time we need per unit work if we use on-demand
        time_needed_on_demand = total_work_needed + (0 if self.env.cluster_type != ClusterType.NONE else self.restart_overhead)
        
        # Calculate slack ratio
        slack_ratio = (remaining_time - time_needed_on_demand) / remaining_time if remaining_time > 0 else -1
        
        if slack_ratio < 0:
            return 0.0  # No time for spot
        elif slack_ratio < 0.1:
            return 0.1  # Very little slack
        elif slack_ratio < 0.3:
            return 0.3  # Moderate slack
        else:
            return 0.7  # Good amount of slack
    
    def _calculate_spot_confidence(self) -> float:
        """Calculate confidence in spot availability based on history."""
        if len(self.spot_history) < 10:
            return 0.5
            
        recent_history = self.spot_history[-20:]
        if not recent_history:
            return 0.5
            
        available_count = sum(1 for h in recent_history if h)
        return available_count / len(recent_history)
    
    def _should_switch_to_ondemand(self, has_spot: bool) -> bool:
        """Determine if we should switch to on-demand based on risk assessment."""
        remaining_time = self.deadline - self.env.elapsed_seconds
        total_work_needed = self.task_duration - sum(self.task_done_time)
        
        if total_work_needed <= 0:
            return False
            
        # Calculate conservative time estimate with spot
        spot_confidence = self._calculate_spot_confidence()
        estimated_spot_availability = max(0.3, spot_confidence)
        
        # Account for restart overheads
        estimated_overheads = 0
        if self.env.cluster_type == ClusterType.NONE or \
           (self.env.cluster_type == ClusterType.SPOT and not has_spot):
            estimated_overheads = self.restart_overhead
            
        # Estimate work rate with spot (considering availability)
        effective_work_rate = estimated_spot_availability
        
        # Time needed if we continue with spot (pessimistic estimate)
        spot_time_needed = (total_work_needed / effective_work_rate) + estimated_overheads
        
        # Time needed with on-demand (optimistic - no interruptions)
        ondemand_time_needed = total_work_needed + estimated_overheads
        
        # Buffer for safety
        safety_buffer = 3600  # 1 hour buffer
        
        # Switch to on-demand if spot might make us miss deadline
        return spot_time_needed > (remaining_time - safety_buffer)
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update spot history
        self.spot_history.append(has_spot)
        if len(self.spot_history) > 100:
            self.spot_history.pop(0)
        
        # Calculate work done so far
        current_work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - current_work_done
        
        # If no work left, do nothing
        if remaining_work <= 0:
            return ClusterType.NONE
        
        remaining_time = self.deadline - self.env.elapsed_seconds
        
        # Emergency mode: if we're running out of time, use on-demand
        time_needed_with_overhead = remaining_work
        if self.env.cluster_type == ClusterType.NONE or \
           (self.env.cluster_type == ClusterType.SPOT and not has_spot):
            time_needed_with_overhead += self.restart_overhead
        
        if time_needed_with_overhead >= remaining_time:
            # Critical: must use on-demand to finish on time
            return ClusterType.ON_DEMAND
        
        # Check if we should switch to on-demand based on risk
        if self._should_switch_to_ondemand(has_spot):
            return ClusterType.ON_DEMAND
        
        # Calculate aggressive factor based on remaining time slack
        aggressiveness = self._get_aggressiveness_factor()
        
        # Track spot runs for pattern detection
        if last_cluster_type == ClusterType.SPOT and has_spot:
            self.consecutive_spot += 1
        else:
            self.consecutive_spot = 0
            
        # Strategy: use spot when available and we have time buffer
        if has_spot:
            # Calculate remaining slack
            slack_ratio = (remaining_time - time_needed_with_overhead) / remaining_time
            
            # Use spot if we have good slack or moderate slack with good spot history
            spot_confidence = self._calculate_spot_confidence()
            
            # Adjust threshold based on spot confidence
            spot_threshold = 0.2  # Base threshold
            if spot_confidence > 0.6:
                spot_threshold = 0.1  # More aggressive with good history
            elif spot_confidence < 0.4:
                spot_threshold = 0.3  # More conservative with bad history
            
            if slack_ratio > spot_threshold:
                return ClusterType.SPOT
            else:
                # Not enough slack for spot, use on-demand
                return ClusterType.ON_DEMAND
        else:
            # Spot not available
            if self.env.cluster_type == ClusterType.SPOT:
                # We were using spot and got preempted
                # If we have time, wait a bit before switching
                if remaining_time > time_needed_with_overhead * 1.5:
                    # Wait for spot to come back
                    return ClusterType.NONE
                else:
                    # Switch to on-demand
                    return ClusterType.ON_DEMAND
            else:
                # We were not using spot
                if remaining_time > time_needed_with_overhead * 1.2:
                    # Wait for spot
                    return ClusterType.NONE
                else:
                    # Need to make progress
                    return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)