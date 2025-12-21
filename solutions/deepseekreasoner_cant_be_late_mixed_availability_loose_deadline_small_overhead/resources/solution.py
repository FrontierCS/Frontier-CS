import numpy as np
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.use_aggressive_spot = False
        self.safety_margin = 0
        self.max_spot_fraction = 0
        self.restart_timer = 0
        
    def solve(self, spec_path: str) -> "Solution":
        try:
            with open(spec_path, 'r') as f:
                content = f.read().strip()
                if content:
                    config = eval(content)
                    self.safety_margin = config.get('safety_margin', 1.0)
                    self.max_spot_fraction = config.get('max_spot_fraction', 0.8)
                    self.use_aggressive_spot = config.get('use_aggressive_spot', False)
        except:
            pass
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update restart timer
        if last_cluster_type == ClusterType.SPOT and self.restart_timer > 0:
            self.restart_timer -= self.env.gap_seconds
        elif self.restart_timer > 0:
            self.restart_timer = max(0, self.restart_timer - self.env.gap_seconds)
        
        # If we're in restart overhead period, don't use spot
        if self.restart_timer > 0 and has_spot:
            has_spot = False
        
        # Calculate progress and remaining work
        total_done = sum(self.task_done_time) if self.task_done_time else 0
        remaining_work = self.task_duration - total_done
        
        # Check if we're done
        if remaining_work <= 0:
            return ClusterType.NONE
        
        # Calculate time left until deadline
        time_left = self.deadline - self.env.elapsed_seconds
        
        # Calculate minimum time needed with on-demand
        min_time_needed = remaining_work
        
        # Calculate buffer needed for potential spot restarts
        buffer_needed = self.restart_overhead * 2  # Allow for 2 restarts
        
        # Emergency mode: if we're running out of time, switch to on-demand
        if time_left < min_time_needed + buffer_needed:
            return ClusterType.ON_DEMAND
        
        # If spot is not available, use on-demand if we must make progress
        if not has_spot:
            # Calculate how long we can afford to wait
            can_wait_time = time_left - min_time_needed - buffer_needed
            
            # If we have buffer, wait (use NONE) to save cost
            if can_wait_time > self.env.gap_seconds * 2:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND
        
        # If we get here, spot is available
        
        # Calculate progress rate needed
        progress_rate_needed = remaining_work / max(time_left - buffer_needed, 0.001)
        
        # Aggressive spot strategy: use spot whenever available if we have buffer
        if self.use_aggressive_spot:
            if time_left > remaining_work * 1.5 + buffer_needed:
                # Start restart timer when switching to spot
                if last_cluster_type != ClusterType.SPOT:
                    self.restart_timer = self.restart_overhead
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        
        # Conservative strategy: balance spot and on-demand based on progress
        spot_ratio = total_done / self.task_duration if self.task_duration > 0 else 0
        
        if spot_ratio < self.max_spot_fraction:
            # We can use more spot
            if time_left > remaining_work * 1.2 + buffer_needed:
                # Start restart timer when switching to spot
                if last_cluster_type != ClusterType.SPOT:
                    self.restart_timer = self.restart_overhead
                return ClusterType.SPOT
        
        # Fallback to on-demand for reliability
        return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
