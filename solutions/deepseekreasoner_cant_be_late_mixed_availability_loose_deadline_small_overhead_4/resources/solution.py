import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_hedge"

    def solve(self, spec_path: str) -> "Solution":
        # Initialize adaptive parameters
        self.safety_factor = 1.5
        self.min_spot_confidence = 0.3
        self.max_wait_steps = 1800  # 30 minutes in seconds
        self.spot_streak = 0
        self.last_spot_available = False
        self.consecutive_unavailable = 0
        self.spot_availability_history = []
        self.spot_success_rate = 0.0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update spot availability tracking
        self.spot_availability_history.append(has_spot)
        if len(self.spot_availability_history) > 100:
            self.spot_availability_history.pop(0)
        
        # Calculate spot success rate from recent history
        if self.spot_availability_history:
            self.spot_success_rate = sum(self.spot_availability_history) / len(self.spot_availability_history)
        
        # Track spot streak
        if last_cluster_type == ClusterType.SPOT and has_spot:
            self.spot_streak += 1
        else:
            self.spot_streak = 0
        
        # Track consecutive unavailable
        if not has_spot and last_cluster_type == ClusterType.SPOT:
            self.consecutive_unavailable += 1
        else:
            self.consecutive_unavailable = 0
        
        self.last_spot_available = has_spot
        
        # Calculate remaining work and time
        total_done = sum(seg.duration for seg in self.task_done_time)
        remaining_work = self.task_duration - total_done
        time_left = self.deadline - self.env.elapsed_seconds
        
        # If work is done, use NONE
        if remaining_work <= 0:
            return ClusterType.NONE
        
        # Calculate required completion rate
        required_rate = remaining_work / time_left if time_left > 0 else float('inf')
        
        # Calculate adaptive safety threshold
        dynamic_safety = self.safety_factor
        
        # Adjust based on spot history and remaining time
        time_pressure = max(0.0, 1.0 - (time_left / (self.deadline * 0.5)))
        if self.spot_success_rate < 0.5:
            dynamic_safety += (0.5 - self.spot_success_rate) * 1.0
        
        # Emergency mode: if we're running out of time
        if time_left < remaining_work * 1.2:  # Less than 20% buffer
            if has_spot and self.spot_streak > 10:  # If spot has been stable
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        
        # Calculate risk score
        spot_risk = (1.0 - self.spot_success_rate) * dynamic_safety
        
        # Check if we can afford restart overhead
        effective_spot_time = self.env.gap_seconds
        if (last_cluster_type != ClusterType.SPOT or not has_spot) and has_spot:
            effective_spot_time = max(0, self.env.gap_seconds - self.restart_overhead)
        
        # Spot decision logic
        if has_spot:
            spot_viable = effective_spot_time > 0
            
            # If spot is viable and we have good streak, use it
            if spot_viable and self.spot_streak > 5:
                return ClusterType.SPOT
            
            # Calculate if we can meet deadline with spot
            if spot_viable:
                estimated_spot_completion = remaining_work / (effective_spot_time / self.env.gap_seconds)
                spot_buffer = time_left - estimated_spot_completion
                
                # Use spot if we have sufficient buffer
                if spot_buffer > self.restart_overhead * 2:
                    return ClusterType.SPOT
                
                # If spot has been reliable recently
                if self.spot_success_rate > 0.7 and spot_buffer > 0:
                    return ClusterType.SPOT
        
        # On-demand fallback conditions
        # 1. No spot available
        # 2. Critical time pressure
        # 3. Spot has been unreliable
        if not has_spot or required_rate > 0.95 or self.consecutive_unavailable > 3:
            return ClusterType.ON_DEMAND
        
        # Calculate if we should wait for spot
        wait_viable = False
        if not has_spot:
            # Estimate when spot might return based on history
            if self.spot_success_rate > 0.5:
                avg_unavailable_duration = 0
                if len(self.spot_availability_history) > 10:
                    # Simple estimate of average unavailable duration
                    count = 0
                    for i in range(1, len(self.spot_availability_history)):
                        if not self.spot_availability_history[i] and self.spot_availability_history[i-1]:
                            count += 1
                    if count > 0:
                        avg_unavailable_duration = len(self.spot_availability_history) / count
                
                # Only wait if we have buffer
                if avg_unavailable_duration > 0 and time_left > remaining_work + avg_unavailable_duration * self.env.gap_seconds:
                    wait_viable = True
        
        if wait_viable and self.consecutive_unavailable < self.max_wait_steps:
            return ClusterType.NONE
        
        # Default to on-demand when uncertain
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
