import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self._state = None
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize state on first call
        if self._state is None:
            self._state = {
                'remaining_work': self.task_duration,
                'time_elapsed': 0,
                'in_overhead': False,
                'overhead_remaining': 0,
                'last_spot_use': False,
                'consecutive_spot_failures': 0,
                'consecutive_on_demand': 0
            }
        
        # Update state
        self._state['time_elapsed'] = self.env.elapsed_seconds
        time_remaining = self.deadline - self._state['time_elapsed']
        
        # Update work progress
        if last_cluster_type != ClusterType.NONE and not self._state['in_overhead']:
            if self._state['remaining_work'] > 0:
                work_done = min(self.env.gap_seconds, self._state['remaining_work'])
                self._state['remaining_work'] -= work_done
        
        # Update overhead state
        if self._state['in_overhead']:
            self._state['overhead_remaining'] -= self.env.gap_seconds
            if self._state['overhead_remaining'] <= 0:
                self._state['in_overhead'] = False
                self._state['overhead_remaining'] = 0
                self._state['consecutive_spot_failures'] = 0
        
        # Calculate safe thresholds
        if self._state['remaining_work'] <= 0:
            return ClusterType.NONE
        
        # Calculate minimum time needed with on-demand (no overhead)
        min_time_needed = self._state['remaining_work']
        
        # Calculate time needed if we use spot with potential overhead
        # Assume worst-case scenario for spot: 50% availability
        conservative_spot_time = self._state['remaining_work'] * 2 + self.restart_overhead * 3
        
        # Calculate safety buffer
        safety_buffer = 3600 * 2  # 2 hours buffer
        
        # Update consecutive counters
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self._state['consecutive_spot_failures'] += 1
        elif last_cluster_type == ClusterType.SPOT and has_spot:
            self._state['consecutive_spot_failures'] = 0
            
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._state['consecutive_on_demand'] += 1
        else:
            self._state['consecutive_on_demand'] = 0
        
        # Strategy decision logic
        # If we're in overhead, don't do anything
        if self._state['in_overhead']:
            return ClusterType.NONE
        
        # Emergency mode: if time is running out, use on-demand
        if time_remaining < min_time_needed + safety_buffer:
            return ClusterType.ON_DEMAND
        
        # If we have many consecutive spot failures, temporarily use on-demand
        if self._state['consecutive_spot_failures'] >= 3:
            # Use on-demand for 2 hours then re-evaluate
            if self._state['consecutive_on_demand'] < 8:  # 8 * 900s = 2 hours
                return ClusterType.ON_DEMAND
        
        # If spot is available and we have time buffer, use spot
        if has_spot and time_remaining > conservative_spot_time:
            return ClusterType.SPOT
        
        # If spot not available but we have time, wait
        if not has_spot and time_remaining > conservative_spot_time + 3600:
            return ClusterType.NONE
        
        # Otherwise use on-demand
        return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)