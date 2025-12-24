import heapq
import math
from typing import List, Tuple, Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        # Initialize state variables
        self._reset_state()
        return self

    def _reset_state(self):
        """Reset internal state variables"""
        self.total_steps = 0
        self.spot_availability_history = []
        self.spot_price_history = []
        self.on_demand_price_history = []
        self.work_remaining_history = []
        self.time_remaining_history = []
        self.decisions = []
        
        # Estimated parameters
        self.spot_unavailable_count = 0
        self.spot_available_count = 0
        self.avg_spot_availability = 0.0
        
        # Adaptive thresholds
        self.safety_margin = 0.1  # Initial 10% safety margin
        self.urgency_threshold = 0.8  # When to switch to on-demand
        self.min_safety_margin = 0.05
        self.max_safety_margin = 0.3
        
        # Window for availability tracking
        self.availability_window = 50

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update statistics
        self.total_steps += 1
        self.spot_availability_history.append(1 if has_spot else 0)
        
        # Keep only recent history for efficiency
        if len(self.spot_availability_history) > self.availability_window:
            self.spot_availability_history.pop(0)
        
        # Calculate current statistics
        if self.spot_availability_history:
            recent_available = sum(self.spot_availability_history)
            recent_total = len(self.spot_availability_history)
            self.avg_spot_availability = recent_available / recent_total
        
        # Calculate remaining work and time
        work_done = sum(self.task_done_time) if self.task_done_time else 0
        work_remaining = max(0, self.task_duration - work_done)
        time_elapsed = self.env.elapsed_seconds
        time_remaining = max(0, self.deadline - time_elapsed)
        
        # Calculate progress metrics
        work_progress = work_done / self.task_duration if self.task_duration > 0 else 0
        time_progress = time_elapsed / self.deadline if self.deadline > 0 else 0
        
        # Calculate critical metrics
        time_per_work = time_remaining / work_remaining if work_remaining > 0 else float('inf')
        required_rate = work_remaining / time_remaining if time_remaining > 0 else float('inf')
        
        # Adjust safety margin based on spot availability
        self._adjust_safety_margin()
        
        # Decision logic
        # Case 1: Very urgent - must use on-demand
        if time_per_work < 1.0:  # Less than 1:1 time:work ratio
            # If we're falling behind, use on-demand
            return ClusterType.ON_DEMAND
        
        # Case 2: Critical situation - low time buffer
        if time_remaining < work_remaining * (1 + self.safety_margin):
            # Not enough time even with perfect spot availability
            return ClusterType.ON_DEMAND
        
        # Case 3: Spot available and we have time buffer
        if has_spot:
            # Calculate effective work rate with spot (accounting for potential interruptions)
            effective_spot_rate = self._estimate_effective_spot_rate()
            
            # If effective spot rate is sufficient to meet deadline with buffer
            time_needed_with_spot = work_remaining / effective_spot_rate if effective_spot_rate > 0 else float('inf')
            time_needed_with_od = work_remaining  # On-demand work rate is 1 work unit per time unit
            
            # Add restart overhead penalty if switching from non-spot to spot
            restart_penalty = self.restart_overhead if last_cluster_type != ClusterType.SPOT else 0
            
            # Calculate if we can afford spot with restart penalty
            if (time_needed_with_spot + restart_penalty) * 1.1 < time_remaining:
                return ClusterType.SPOT
            elif time_needed_with_od * 1.2 < time_remaining:
                # We have some buffer but not enough for spot interruptions
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND
        else:
            # Spot not available
            if time_remaining < work_remaining * 1.2:  # Tight schedule
                return ClusterType.ON_DEMAND
            else:
                # Can afford to wait for spot
                return ClusterType.NONE
    
    def _adjust_safety_margin(self):
        """Adjust safety margin based on observed spot availability"""
        if len(self.spot_availability_history) < 10:
            return
        
        recent_availability = self.avg_spot_availability
        
        # Lower safety margin when spot is reliably available
        if recent_availability > 0.7:  # High availability
            self.safety_margin = max(self.min_safety_margin, 
                                    self.safety_margin * 0.9)  # Reduce margin
        elif recent_availability < 0.3:  # Low availability
            self.safety_margin = min(self.max_safety_margin, 
                                    self.safety_margin * 1.1)  # Increase margin
    
    def _estimate_effective_spot_rate(self) -> float:
        """Estimate effective work rate using spot instances"""
        if not self.spot_availability_history:
            return 0.7  # Conservative default
        
        # Calculate probability of consecutive available steps
        window = min(10, len(self.spot_availability_history))
        recent = self.spot_availability_history[-window:]
        
        # Estimate average uninterrupted run length
        current_run = 0
        max_run = 0
        for available in recent:
            if available:
                current_run += 1
                max_run = max(max_run, current_run)
            else:
                current_run = 0
        
        # Base rate adjusted by availability and restart overhead
        base_rate = self.avg_spot_availability
        overhead_penalty = self.restart_overhead / (max_run + 1) if max_run > 0 else 0
        
        effective_rate = base_rate * (1 - overhead_penalty)
        return max(0.3, min(0.95, effective_rate))  # Clamp to reasonable range

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
