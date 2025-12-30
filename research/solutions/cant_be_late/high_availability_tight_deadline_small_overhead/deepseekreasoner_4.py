import json
import math
from typing import Dict, List, Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.config = None
        self.remaining_work = 0.0
        self.safety_margin = 0.0
        self.consecutive_spots = 0
        self.last_spot_available = True
        self.spot_availability_history = []
        self.spot_unavailable_streak = 0
        
    def solve(self, spec_path: str) -> "Solution":
        try:
            with open(spec_path, 'r') as f:
                self.config = json.load(f)
        except:
            self.config = {}
        
        self.remaining_work = self.task_duration
        # Calculate safety margin based on deadline slack
        slack = self.deadline - self.task_duration
        # Reserve 30% of slack for safety
        self.safety_margin = slack * 0.3
        
        return self
    
    def _calculate_aggressiveness(self) -> float:
        """Calculate how aggressive we should be based on remaining time."""
        remaining_time = self.deadline - self.env.elapsed_seconds
        work_ratio = self.remaining_work / self.task_duration if self.task_duration > 0 else 1.0
        time_ratio = remaining_time / self.deadline
        
        # More aggressive as time runs out or work remains high
        if remaining_time <= self.safety_margin:
            return 1.0  # Must use on-demand
        elif work_ratio > time_ratio * 1.2:
            return 0.8  # Behind schedule
        elif work_ratio > time_ratio:
            return 0.6  # Slightly behind
        else:
            return 0.3  # Ahead of schedule
    
    def _get_spot_availability_probability(self) -> float:
        """Estimate spot availability probability from history."""
        if not self.spot_availability_history:
            return 0.5
        
        recent = self.spot_availability_history[-min(50, len(self.spot_availability_history)):]
        return sum(recent) / len(recent)
    
    def _should_use_spot(self, has_spot: bool, aggressiveness: float) -> bool:
        """Determine if we should use spot based on multiple factors."""
        if not has_spot:
            return False
            
        remaining_time = self.deadline - self.env.elapsed_seconds
        time_per_work = remaining_time / max(self.remaining_work, 0.1)
        
        # Don't use spot if we're very tight on time
        if remaining_time <= self.safety_margin:
            return False
            
        # Don't use spot if we're behind schedule
        if aggressiveness > 0.7:
            return False
            
        # Avoid long consecutive spot runs to minimize risk
        if self.consecutive_spots > 10:
            return False
            
        # Check spot availability probability
        spot_prob = self._get_spot_availability_probability()
        if spot_prob < 0.5 and aggressiveness > 0.4:
            return False
            
        return True
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update state
        self.last_spot_available = has_spot
        self.spot_availability_history.append(1 if has_spot else 0)
        
        # Update work tracking
        if last_cluster_type != ClusterType.NONE:
            progress = self.env.gap_seconds
            if last_cluster_type == ClusterType.SPOT:
                # Apply restart overhead if we just switched from spot to something else
                if (self.env.cluster_type == ClusterType.SPOT and 
                    last_cluster_type != ClusterType.SPOT):
                    progress -= self.restart_overhead
            self.remaining_work = max(0, self.remaining_work - progress)
        
        # Update consecutive spots counter
        if last_cluster_type == ClusterType.SPOT:
            self.consecutive_spots += 1
        else:
            self.consecutive_spots = 0
            
        # Update spot unavailable streak
        if not has_spot:
            self.spot_unavailable_streak += 1
        else:
            self.spot_unavailable_streak = 0
        
        # Check if we're done
        if self.remaining_work <= 0:
            return ClusterType.NONE
            
        # Calculate how aggressive we need to be
        aggressiveness = self._calculate_aggressiveness()
        
        # Check if we must use on-demand to meet deadline
        remaining_time = self.deadline - self.env.elapsed_seconds
        min_time_needed = self.remaining_work
        
        if remaining_time <= min_time_needed + self.restart_overhead:
            # Must use on-demand to guarantee completion
            return ClusterType.ON_DEMAND
        
        # Determine action
        if self._should_use_spot(has_spot, aggressiveness):
            return ClusterType.SPOT
        elif remaining_time <= min_time_needed + self.safety_margin:
            # Use on-demand when safety margin is breached
            return ClusterType.ON_DEMAND
        elif self.spot_unavailable_streak > 5:
            # If spot has been unavailable for a while, consider on-demand
            if aggressiveness > 0.5:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE
        else:
            # Wait for better conditions
            return ClusterType.NONE
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)