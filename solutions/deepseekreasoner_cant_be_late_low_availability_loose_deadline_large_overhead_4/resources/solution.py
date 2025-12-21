import argparse
import math
from typing import List, Optional, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_threshold"

    def solve(self, spec_path: str) -> "Solution":
        # Initialize state variables
        self.spot_history = []
        self.consecutive_spot_failures = 0
        self.remaining_work = self.task_duration
        self.time_buffer = self.deadline - self.task_duration
        
        # Adaptive parameters
        self.spot_confidence = 0.7
        self.min_spot_confidence = 0.3
        self.max_spot_confidence = 0.9
        self.emergency_threshold = 0.3  # Use OD if less than 30% of buffer remains
        
        # State tracking
        self.last_spot_available = True
        self.overhead_timer = 0
        self.in_overhead = False
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update spot history
        self.spot_history.append(has_spot)
        if len(self.spot_history) > 100:  # Keep recent history
            self.spot_history.pop(0)
        
        # Update overhead state
        if self.in_overhead:
            self.overhead_timer -= self.env.gap_seconds
            if self.overhead_timer <= 0:
                self.in_overhead = False
                self.overhead_timer = 0
        
        # Calculate progress and remaining time
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        work_done = sum(self.task_done_time)
        self.remaining_work = self.task_duration - work_done
        
        # If work is done, stop
        if self.remaining_work <= 0:
            return ClusterType.NONE
        
        # Emergency check: if we're running out of time, use on-demand
        if remaining_time < self.remaining_work + self.restart_overhead:
            return ClusterType.ON_DEMAND
        
        # Calculate adaptive threshold based on remaining buffer
        time_buffer_used = elapsed - work_done
        buffer_ratio = (self.time_buffer - time_buffer_used) / self.time_buffer
        
        # Adjust spot confidence based on recent history
        if len(self.spot_history) >= 10:
            recent_availability = sum(self.spot_history[-10:]) / 10.0
            if recent_availability < 0.5:
                self.spot_confidence = max(self.min_spot_confidence, self.spot_confidence - 0.1)
            elif recent_availability > 0.8:
                self.spot_confidence = min(self.max_spot_confidence, self.spot_confidence + 0.1)
        
        # Check if we're in overhead from previous spot restart
        if self.in_overhead:
            # During overhead, prefer to wait unless we're behind schedule
            if buffer_ratio < self.emergency_threshold:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE
        
        # Update consecutive failures counter
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_spot_failures += 1
            if self.consecutive_spot_failures >= 2:
                # After multiple failures, be more conservative
                self.spot_confidence = max(self.min_spot_confidence, self.spot_confidence - 0.2)
        else:
            self.consecutive_spot_failures = 0
        
        # Decision logic
        if not has_spot:
            # Spot not available this step
            if buffer_ratio < self.emergency_threshold:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE
        
        # Spot is available - decide whether to use it
        if last_cluster_type == ClusterType.SPOT and has_spot:
            # Continue using spot if it's working
            return ClusterType.SPOT
        
        # Consider switching to spot
        spot_probability = self.spot_confidence * (1.0 + buffer_ratio) / 2.0
        
        # Calculate risk score
        time_needed = self.remaining_work
        if last_cluster_type != ClusterType.SPOT:
            time_needed += self.restart_overhead
        
        risk_score = time_needed / remaining_time
        
        if risk_score > 1.0:
            # We're behind schedule, use on-demand
            return ClusterType.ON_DEMAND
        
        if buffer_ratio < self.emergency_threshold:
            # Low buffer, be conservative
            if risk_score > 0.8:
                return ClusterType.ON_DEMAND
        
        if risk_score < 0.7 and buffer_ratio > 0.4:
            # Good buffer, try spot with probability
            import random
            if random.random() < spot_probability:
                if last_cluster_type != ClusterType.SPOT:
                    self.in_overhead = True
                    self.overhead_timer = self.restart_overhead
                return ClusterType.SPOT
        
        # Default: use on-demand if risk is moderate, else wait
        if risk_score > 0.6 or buffer_ratio < 0.2:
            return ClusterType.ON_DEMAND
        
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
