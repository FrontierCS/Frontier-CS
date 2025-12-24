import os
import pickle
import numpy as np
from typing import List, Dict, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.strategy_state = {}
        self.availability_trace = []
        self.availability_index = 0
        
    def solve(self, spec_path: str) -> "Solution":
        """Initialize the solution with any needed configuration."""
        # Load spot availability trace if provided in spec
        if os.path.exists(spec_path):
            try:
                with open(spec_path, 'rb') as f:
                    spec = pickle.load(f)
                    self.availability_trace = spec.get('spot_availability', [])
            except:
                pass
                
        # Initialize strategy state
        self.strategy_state = {
            'consecutive_unavailable': 0,
            'spot_usage_count': 0,
            'last_switch_time': 0,
            'restart_pending': False,
            'restart_end_time': 0,
            'total_spot_time': 0,
            'total_od_time': 0,
            'work_remaining': self.task_duration,
            'last_work_time': 0,
            'safety_buffer': 4 * 3600,  # 4 hours in seconds
            'aggressiveness': 0.7,  # Controls risk appetite (0-1)
        }
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """Main decision function for each time step."""
        current_time = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        # Update restart status
        if self.strategy_state['restart_pending'] and current_time >= self.strategy_state['restart_end_time']:
            self.strategy_state['restart_pending'] = False
            
        # Calculate work done since last step
        if last_cluster_type != ClusterType.NONE and not self.strategy_state['restart_pending']:
            work_done = gap
            self.strategy_state['work_remaining'] = max(0, self.strategy_state['work_remaining'] - work_done)
            
            # Update time counters
            if last_cluster_type == ClusterType.SPOT:
                self.strategy_state['total_spot_time'] += gap
                self.strategy_state['spot_usage_count'] += 1
            elif last_cluster_type == ClusterType.ON_DEMAND:
                self.strategy_state['total_od_time'] += gap
                
        # Check if work is complete
        if self.strategy_state['work_remaining'] <= 0:
            return ClusterType.NONE
            
        # Calculate time remaining until deadline
        time_remaining = self.deadline - current_time
        
        # Safety check: if very little time left, use on-demand
        min_time_needed = self.strategy_state['work_remaining']
        if self.strategy_state['restart_pending']:
            min_time_needed += (self.strategy_state['restart_end_time'] - current_time)
            
        if time_remaining <= min_time_needed + 3600:  # Less than 1 hour buffer
            return ClusterType.ON_DEMAND if has_spot else ClusterType.NONE
        
        # Update availability tracking
        if has_spot:
            self.strategy_state['consecutive_unavailable'] = 0
        else:
            self.strategy_state['consecutive_unavailable'] += 1
            
        # Adaptive strategy based on progress
        progress_ratio = 1 - (self.strategy_state['work_remaining'] / self.task_duration)
        time_ratio = current_time / self.deadline
        
        # Calculate risk score (0-1, higher = more aggressive)
        base_risk = self.strategy_state['aggressiveness']
        time_pressure = max(0, 1 - (time_remaining / (self.task_duration * 1.1)))
        risk_score = base_risk * (1 - time_pressure)  # Be less aggressive as deadline approaches
        
        # Decision logic
        if has_spot:
            # Consider using spot
            spot_viable = self._should_use_spot(current_time, time_remaining, risk_score)
            
            if spot_viable:
                # Check if we need to restart
                if last_cluster_type != ClusterType.SPOT and last_cluster_type != ClusterType.NONE:
                    # Switching to spot from on-demand incurs restart
                    if not self.strategy_state['restart_pending']:
                        self.strategy_state['restart_pending'] = True
                        self.strategy_state['restart_end_time'] = current_time + self.restart_overhead
                    return ClusterType.NONE
                return ClusterType.SPOT
            else:
                # Use on-demand instead
                return ClusterType.ON_DEMAND
        else:
            # Spot not available
            if last_cluster_type == ClusterType.SPOT:
                # Spot was preempted, need restart
                if not self.strategy_state['restart_pending']:
                    self.strategy_state['restart_pending'] = True
                    self.strategy_state['restart_end_time'] = current_time + self.restart_overhead
                return ClusterType.NONE
            
            # If we have pending restart, wait
            if self.strategy_state['restart_pending']:
                return ClusterType.NONE
                
            # If we were using on-demand, continue
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
                
            # Otherwise, use on-demand if we need to make progress
            if time_remaining < self.strategy_state['work_remaining'] * 1.5:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE
    
    def _should_use_spot(self, current_time: float, time_remaining: float, risk_score: float) -> bool:
        """Determine if spot should be used based on current conditions."""
        # If restart is pending, cannot use spot
        if self.strategy_state['restart_pending']:
            return False
            
        # Calculate conservative estimate of time needed with spot
        # Account for potential restarts based on historical usage
        avg_spot_uptime = 0
        if self.strategy_state['spot_usage_count'] > 0:
            avg_spot_uptime = self.strategy_state['total_spot_time'] / self.strategy_state['spot_usage_count']
        
        # Estimate number of additional restarts needed
        work_remaining = self.strategy_state['work_remaining']
        if avg_spot_uptime > 0:
            estimated_restarts = max(0, (work_remaining / avg_spot_uptime) - 1)
        else:
            estimated_restarts = 3  # Conservative default
            
        # Time needed with spot = work time + restart overheads
        spot_time_needed = work_remaining + (estimated_restarts * self.restart_overhead * 0.5)
        
        # Add safety margin based on risk score
        safety_margin = self.strategy_state['safety_buffer'] * (1 - risk_score)
        
        # Check if we have enough time
        if time_remaining < spot_time_needed + safety_margin:
            return False
            
        # Consider spot reliability
        if self.strategy_state['consecutive_unavailable'] > 10:
            return False
            
        # If we have good progress and time, use spot
        progress = 1 - (work_remaining / self.task_duration)
        if progress > 0.8 and time_remaining > work_remaining * 2:
            return True
            
        # Default: use spot if we have sufficient time buffer
        return time_remaining > spot_time_needed + (safety_margin * 0.5)
    
    @classmethod
    def _from_args(cls, parser):
        """Required for evaluator instantiation."""
        args, _ = parser.parse_known_args()
        return cls(args)
