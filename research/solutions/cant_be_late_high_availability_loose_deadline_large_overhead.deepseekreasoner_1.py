import time
from typing import Dict, Any
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "efficient_hybrid_scheduler"
    
    def solve(self, spec_path: str) -> "Solution":
        # Initialize state variables
        self.state = {
            'spot_availability_history': [],
            'current_restart_timer': 0,
            'consecutive_spot_failures': 0,
            'spot_reliability': 0.6,  # Conservative initial estimate
            'critical_zone_start': self.deadline - 6 * 3600,  # Last 6 hours
            'spot_streak': 0,
            'last_decision': ClusterType.NONE,
            'progress_rate': 0.0,
            'work_done': 0.0,
            'last_work_time': 0.0,
            'safety_buffer': 2 * self.restart_overhead,
        }
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update spot availability history
        self.state['spot_availability_history'].append(has_spot)
        if len(self.state['spot_availability_history']) > 100:
            self.state['spot_availability_history'].pop(0)
        
        # Calculate current progress metrics
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        # Update restart timer
        if self.state['current_restart_timer'] > 0:
            self.state['current_restart_timer'] = max(0, self.state['current_restart_timer'] - gap)
        
        # Calculate work done in last interval if we were running
        if last_cluster_type != ClusterType.NONE and self.state['current_restart_timer'] == 0:
            work_done = gap
            self.state['work_done'] += work_done
            self.state['last_work_time'] = elapsed
        
        # Calculate remaining work and time
        total_done = sum(self.task_done_time) if self.task_done_time else 0
        remaining_work = self.task_duration - total_done
        time_remaining = self.deadline - elapsed
        
        # Calculate progress rate (work per second)
        if elapsed > 0:
            self.state['progress_rate'] = total_done / elapsed
        
        # Update spot reliability estimate
        if len(self.state['spot_availability_history']) >= 10:
            recent = self.state['spot_availability_history'][-10:]
            self.state['spot_reliability'] = sum(recent) / len(recent)
        
        # Update consecutive spot failures
        if not has_spot and last_cluster_type == ClusterType.SPOT:
            self.state['consecutive_spot_failures'] += 1
        else:
            self.state['consecutive_spot_failures'] = 0
        
        # Update spot streak
        if last_cluster_type == ClusterType.SPOT and has_spot:
            self.state['spot_streak'] += 1
        else:
            self.state['spot_streak'] = 0
        
        # CRITICAL: If we're in the final stretch and behind schedule, use on-demand
        if elapsed >= self.state['critical_zone_start']:
            expected_time_remaining = remaining_work / self.state['progress_rate'] if self.state['progress_rate'] > 0 else float('inf')
            if expected_time_remaining > time_remaining - self.state['safety_buffer']:
                self.state['last_decision'] = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND
        
        # Calculate conservative time estimate with spot
        spot_success_prob = max(0.01, self.state['spot_reliability'] - 0.1)  # Conservative estimate
        expected_spot_time = remaining_work / spot_success_prob if spot_success_prob > 0 else float('inf')
        expected_spot_time += self.state['consecutive_spot_failures'] * self.restart_overhead
        
        # Calculate on-demand time
        ondemand_time = remaining_work
        if last_cluster_type != ClusterType.ON_DEMAND:
            ondemand_time += self.restart_overhead - self.state['current_restart_timer']
        
        # Decision logic
        decision = ClusterType.NONE
        
        # If spot has been reliable recently and we have time, try spot
        if (has_spot and 
            self.state['spot_streak'] >= 3 and  # Spot has been stable
            expected_spot_time < time_remaining - self.state['safety_buffer'] and
            self.state['consecutive_spot_failures'] < 2):
            
            decision = ClusterType.SPOT
        
        # If spot is available but we're more cautious
        elif (has_spot and
              expected_spot_time < time_remaining - self.state['safety_buffer'] * 2 and
              remaining_work > gap * 5):  # Enough work left to justify overhead
            
            # Only use spot if reliability is decent
            if self.state['spot_reliability'] > 0.4:
                decision = ClusterType.SPOT
        
        # If we're falling behind or spot is unreliable, use on-demand
        elif (ondemand_time > time_remaining - self.state['safety_buffer'] or
              (not has_spot and remaining_work > 0) or
              self.state['consecutive_spot_failures'] >= 3):
            
            decision = ClusterType.ON_DEMAND
        
        # If we're ahead of schedule and spot isn't available, wait
        elif (remaining_work > 0 and 
              ondemand_time < time_remaining - self.state['safety_buffer'] * 3):
            
            decision = ClusterType.NONE
        
        # Default to on-demand if we have work to do
        elif remaining_work > 0:
            decision = ClusterType.ON_DEMAND
        
        # Safety check: don't use spot if unavailable
        if decision == ClusterType.SPOT and not has_spot:
            decision = ClusterType.ON_DEMAND if remaining_work > 0 else ClusterType.NONE
        
        # Update restart timer if switching to a running state
        if (decision != ClusterType.NONE and 
            decision != last_cluster_type and
            last_cluster_type != ClusterType.NONE):
            
            self.state['current_restart_timer'] = self.restart_overhead
        
        self.state['last_decision'] = decision
        return decision
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)