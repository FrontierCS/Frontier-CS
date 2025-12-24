import argparse
import math
from typing import List, Tuple
from enum import Enum

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.spot_price = None
        self.on_demand_price = None
        self.work_remaining = None
        self.time_remaining = None
        self.overhead_remaining = 0
        self.current_cluster = ClusterType.NONE
        self.last_decision = ClusterType.NONE
        self.spot_history = []
        self.consecutive_spot_failures = 0
        self.predicted_spot_reliability = 0.7
        self.switch_pending = False
        self.conservative_threshold = 0.3
        self.aggressive_threshold = 0.6
        self.min_spot_run_time = 2.0 * 3600  # 2 hours in seconds
        self.last_spot_start = None
        self.spot_run_duration = 0
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def _update_state(self, last_cluster_type: ClusterType, has_spot: bool):
        """Update internal state tracking"""
        # Update spot availability history
        self.spot_history.append(has_spot)
        if len(self.spot_history) > 100:
            self.spot_history.pop(0)
            
        # Update spot reliability prediction
        if len(self.spot_history) > 10:
            self.predicted_spot_reliability = sum(self.spot_history) / len(self.spot_history)
            
        # Update work remaining
        work_done = sum(self.task_done_time) if self.task_done_time else 0
        self.work_remaining = max(0, self.task_duration - work_done)
        
        # Update time remaining
        self.time_remaining = max(0, self.deadline - self.env.elapsed_seconds)
        
        # Update overhead tracking
        if self.switch_pending:
            self.overhead_remaining = max(0, self.overhead_remaining - self.env.gap_seconds)
            if self.overhead_remaining <= 0:
                self.switch_pending = False
        
        # Update spot run tracking
        if last_cluster_type == ClusterType.SPOT:
            self.spot_run_duration += self.env.gap_seconds
        else:
            self.spot_run_duration = 0
            if last_cluster_type == ClusterType.ON_DEMAND:
                self.last_spot_start = None
        
        # Track consecutive spot failures
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_spot_failures += 1
        else:
            self.consecutive_spot_failures = 0
            
        self.current_cluster = last_cluster_type
    
    def _calculate_urgency(self) -> float:
        """Calculate urgency factor (0-1) based on time remaining"""
        if self.time_remaining <= 0 or self.work_remaining <= 0:
            return 1.0
            
        # Theoretical minimum time needed (assuming continuous work)
        min_time_needed = self.work_remaining
        
        # If we're in overhead, account for it
        if self.switch_pending:
            min_time_needed += self.overhead_remaining
            
        # Add safety buffer for potential future overheads
        safety_buffer = self.restart_overhead * 2
        
        # Calculate urgency
        time_available = self.time_remaining
        if time_available <= safety_buffer:
            return 1.0
            
        effective_time = time_available - safety_buffer
        
        if min_time_needed <= 0:
            return 0.0
            
        ratio = min_time_needed / effective_time
        return min(1.0, max(0.0, ratio))
    
    def _should_use_spot(self, has_spot: bool) -> bool:
        """Determine if spot should be used"""
        if not has_spot:
            return False
            
        urgency = self._calculate_urgency()
        
        # If very urgent, avoid spot
        if urgency > self.aggressive_threshold:
            return False
            
        # If we've had recent spot failures, be cautious
        if self.consecutive_spot_failures > 2:
            return False
            
        # Don't start spot if we don't have time for a reasonable run
        min_viable_spot_time = self.min_spot_run_time + self.restart_overhead
        if self.time_remaining < min_viable_spot_time:
            return False
            
        # Check if we have enough buffer for potential overhead
        safety_margin = self.restart_overhead * 3
        time_needed_with_overhead = self.work_remaining + safety_margin
        
        if self.time_remaining < time_needed_with_overhead:
            # In tight situations, use spot only if very reliable
            return self.predicted_spot_reliability > 0.8
        
        # Base decision on predicted reliability and urgency
        reliability_threshold = 0.5 + (urgency * 0.3)
        return self.predicted_spot_reliability > reliability_threshold
    
    def _should_use_on_demand(self) -> bool:
        """Determine if on-demand should be used"""
        urgency = self._calculate_urgency()
        
        # If we're very urgent, use on-demand
        if urgency > self.aggressive_threshold:
            return True
            
        # If we're in a switch overhead, continue with current
        if self.switch_pending and self.current_cluster == ClusterType.ON_DEMAND:
            return True
            
        # If work is almost done and time is tight
        if self.work_remaining < 3600 and urgency > 0.2:  # Less than 1 hour work left
            return True
            
        # Default to on-demand only when spot is not viable
        return False
    
    def _should_pause(self) -> bool:
        """Determine if we should pause"""
        urgency = self._calculate_urgency()
        
        # Don't pause if urgent
        if urgency > 0.7:
            return False
            
        # Don't pause if we're in the middle of work
        if self.current_cluster != ClusterType.NONE and not self.switch_pending:
            return False
            
        # Pause if waiting for better spot conditions
        if (self.current_cluster == ClusterType.NONE and 
            self.predicted_spot_reliability < 0.3 and
            urgency < 0.4):
            return True
            
        return False
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update internal state
        self._update_state(last_cluster_type, has_spot)
        
        # Check if work is complete
        if self.work_remaining <= 0:
            return ClusterType.NONE
            
        # Check if we've run out of time
        if self.time_remaining <= 0:
            return ClusterType.NONE
        
        # Determine next action
        if self._should_pause():
            decision = ClusterType.NONE
        elif self._should_use_spot(has_spot):
            decision = ClusterType.SPOT
        elif self._should_use_on_demand():
            decision = ClusterType.ON_DEMAND
        else:
            # Default to on-demand if all else fails
            decision = ClusterType.ON_DEMAND
        
        # Check if this is a switch from active cluster
        if (last_cluster_type != ClusterType.NONE and 
            decision != last_cluster_type and
            decision != ClusterType.NONE):
            self.switch_pending = True
            self.overhead_remaining = self.restart_overhead
        
        self.last_decision = decision
        return decision
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
