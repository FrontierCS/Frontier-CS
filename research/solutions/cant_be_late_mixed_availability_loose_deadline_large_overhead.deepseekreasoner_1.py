import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.config = {}
        self.last_spot_state = True
        self.spot_availability_history = []
        self.spot_reliability = 0.0
        self.steps_since_start = 0
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update reliability statistics
        self.steps_since_start += 1
        self.spot_availability_history.append(has_spot)
        if len(self.spot_availability_history) > 100:
            self.spot_availability_history.pop(0)
        
        self.spot_reliability = (
            sum(self.spot_availability_history) / len(self.spot_availability_history) 
            if self.spot_availability_history else 0.0
        )
        
        # Calculate progress metrics
        total_work_done = sum((end - start) for start, end, _ in self.task_done_time)
        remaining_work = self.task_duration - total_work_done
        time_elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - time_elapsed
        
        # Calculate conservative completion times
        step_seconds = self.env.gap_seconds
        overhead_steps = max(0, math.ceil(self.restart_overhead / step_seconds))
        
        # Estimate spot reliability for remaining time
        if len(self.spot_availability_history) >= 10:
            recent_reliability = sum(self.spot_availability_history[-10:]) / 10.0
        else:
            recent_reliability = self.spot_reliability
        
        # Adjust reliability with safety margin
        adjusted_reliability = recent_reliability * 0.8  # 20% safety margin
        
        # Calculate effective work rates
        effective_spot_rate = adjusted_reliability if has_spot else 0.0
        effective_od_rate = 1.0  # On-demand always works
        
        # Calculate required steps to finish
        steps_needed_od = math.ceil(remaining_work / (step_seconds * effective_od_rate))
        steps_needed_spot = math.ceil(remaining_work / (step_seconds * max(effective_spot_rate, 0.01)))
        
        # Calculate available steps
        available_steps = math.floor(time_remaining / step_seconds)
        
        # Calculate risk factor - how close we are to deadline
        risk_factor = 1.0 - (time_remaining / (self.deadline - 0))
        
        # Dynamic threshold based on risk and reliability
        reliability_threshold = 0.3 + risk_factor * 0.4  # 0.3 to 0.7
        
        # Decision logic
        if not has_spot:
            # No spot available
            if remaining_work <= 0:
                return ClusterType.NONE
            elif steps_needed_od > available_steps - 2:  # Buffer of 2 steps
                return ClusterType.ON_DEMAND
            elif recent_reliability > reliability_threshold:
                return ClusterType.NONE  # Wait for spot to return
            else:
                return ClusterType.ON_DEMAND
        
        # Spot is available
        if remaining_work <= 0:
            return ClusterType.NONE
        
        # Check if we're in critical time
        if steps_needed_od > available_steps - 5:  # Critical: within 5 steps of deadline
            return ClusterType.ON_DEMAND
        
        # Calculate efficiency ratio
        od_cost = 3.06  # $/hr from problem description
        spot_cost = 0.97  # $/hr from problem description
        cost_ratio = od_cost / spot_cost
        
        # Estimate expected interruptions
        if recent_reliability < 0.5 and self.last_spot_state and risk_factor > 0.3:
            # Unreliable spot, moderate risk - use on-demand
            return ClusterType.ON_DEMAND
        
        # Use spot if we have enough time buffer
        time_buffer_needed = self.restart_overhead * 2  # Allow for one interruption
        if time_remaining - (steps_needed_spot * step_seconds) > time_buffer_needed:
            if recent_reliability > 0.6 or risk_factor < 0.5:
                return ClusterType.SPOT
        
        # Fallback to on-demand for safety
        if risk_factor > 0.6 or steps_needed_spot > available_steps * 0.9:
            return ClusterType.ON_DEMAND
        
        # Default to spot if available and not critical
        return ClusterType.SPOT
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)