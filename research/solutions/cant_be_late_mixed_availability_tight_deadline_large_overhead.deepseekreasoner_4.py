import numpy as np
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_threshold"
    
    def solve(self, spec_path: str) -> "Solution":
        # Initialize adaptive thresholds and state tracking
        self.spot_price = 0.97  # $/hr
        self.ondemand_price = 3.06  # $/hr
        self.price_ratio = self.spot_price / self.ondemand_price
        
        # Adaptive parameters
        self.min_spot_confidence = 0.6  # Minimum confidence to use spot
        self.spot_streak_threshold = 5  # Consecutive spot availability to lower threshold
        self.emergency_threshold = 0.9  # When to panic and use on-demand
        
        # State tracking
        self.spot_streak = 0
        self.work_remaining = self.task_duration
        self.critical_time = None
        
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update work remaining
        if last_cluster_type != ClusterType.NONE:
            work_done = self.env.gap_seconds
            self.work_remaining = max(0, self.work_remaining - work_done)
        
        # Check if we're done
        if self.work_remaining <= 0:
            return ClusterType.NONE
        
        # Calculate time pressure
        time_elapsed = self.env.elapsed_seconds
        time_left = self.deadline - time_elapsed
        
        # Calculate remaining work including potential overhead
        effective_work = self.work_remaining
        
        # If we need to restart, add overhead (worst case)
        if last_cluster_type == ClusterType.NONE:
            effective_work += self.restart_overhead
        
        # Calculate minimum time needed (if using only on-demand)
        min_time_needed = effective_work
        
        # Time pressure ratio: how tight is our schedule
        time_pressure = min_time_needed / time_left if time_left > 0 else float('inf')
        
        # Update spot streak counter
        if has_spot:
            self.spot_streak = min(self.spot_streak + 1, self.spot_streak_threshold * 2)
        else:
            self.spot_streak = max(self.spot_streak - 2, 0)
        
        # Adaptive confidence threshold based on streak and time pressure
        base_confidence = self.min_spot_confidence
        streak_bonus = min(self.spot_streak / self.spot_streak_threshold * 0.3, 0.3)
        adaptive_confidence = base_confidence + streak_bonus
        
        # Emergency mode: if we're running out of time
        if time_pressure > self.emergency_threshold:
            # Critical time - must use on-demand to guarantee completion
            if has_spot and time_pressure < 0.95:  # Slight buffer
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        # Strategic decision making
        if has_spot:
            # Calculate cost-benefit ratio
            spot_benefit = self.ondemand_price - self.spot_price
            
            # Adjust threshold based on time pressure
            time_risk = min(time_pressure * 2, 1.0)  # Scale time pressure
            required_confidence = adaptive_confidence * (1 + time_risk * 0.5)
            
            # Estimate probability of successful spot usage
            # Use streak as proxy for reliability
            spot_reliability = min(self.spot_streak / 10, 0.9)
            
            # Expected value calculation
            if spot_reliability > required_confidence:
                return ClusterType.SPOT
        
        # Fallback strategies
        if time_pressure > 0.7:
            # Moderate time pressure - use on-demand
            return ClusterType.ON_DEMAND
        elif time_pressure < 0.3:
            # Plenty of time - pause to save money if spot unavailable
            if not has_spot:
                return ClusterType.NONE
        
        # Default to on-demand for safety
        return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)