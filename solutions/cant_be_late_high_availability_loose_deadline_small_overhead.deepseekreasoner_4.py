import json
import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.safety_factor = 1.0
        self.use_spot_threshold = 0.0
        
    def solve(self, spec_path: str) -> "Solution":
        try:
            with open(spec_path, 'r') as f:
                spec = json.load(f)
                self.safety_factor = float(spec.get("safety_factor", 1.0))
                self.use_spot_threshold = float(spec.get("use_spot_threshold", 0.0))
        except (FileNotFoundError, json.JSONDecodeError):
            self.safety_factor = 1.0
            self.use_spot_threshold = 0.0
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work
        completed = sum(self.task_done_time)
        remaining_work = self.task_duration - completed
        
        if remaining_work <= 0:
            return ClusterType.NONE
        
        # Calculate time remaining until deadline
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        # Calculate effective remaining time considering restart overhead
        # We need to be more conservative as we approach deadline
        time_needed_on_demand = remaining_work
        time_needed_spot = remaining_work + self.restart_overhead
        
        # Dynamic safety factor based on progress
        progress = completed / self.task_duration
        dynamic_safety = self.safety_factor * (1.0 + (1.0 - progress) * 0.5)
        
        # Check if we're in critical zone
        critical_zone = time_remaining < time_needed_on_demand * 1.2
        
        # Decide based on availability and safety
        if critical_zone:
            # In critical zone, prefer on-demand to guarantee completion
            return ClusterType.ON_DEMAND
        elif has_spot:
            # Calculate if we can afford spot interruptions
            # Use spot if we have enough buffer time
            time_buffer_needed = time_needed_spot * dynamic_safety
            if time_remaining > time_buffer_needed:
                # Only use spot if we're not currently in restart overhead
                # and spot availability is good
                if last_cluster_type == ClusterType.SPOT or last_cluster_type == ClusterType.NONE:
                    return ClusterType.SPOT
                else:
                    # If we were using on-demand, continue if spot was recently interrupted
                    return ClusterType.SPOT
            else:
                # Not enough buffer, use on-demand
                return ClusterType.ON_DEMAND
        else:
            # No spot available
            if time_remaining > time_needed_on_demand * 1.1:
                # Wait for spot to become available
                return ClusterType.NONE
            else:
                # Need to make progress, use on-demand
                return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
