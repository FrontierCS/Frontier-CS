import os
import json
import math
from typing import List, Dict, Tuple, Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args=None):
        super().__init__(args)
        self.spot_price = 0.97
        self.od_price = 3.06
        self.overhead_seconds = 720  # 12 minutes = 720 seconds
        self.task_hours = 48
        self.deadline_hours = 70
        self.slack_hours = 22
        
        # State variables
        self.remaining_work = 0
        self.remaining_time = 0
        self.time_since_last_switch = 0
        self.in_overhead = False
        self.overhead_remaining = 0
        self.spot_availability_history = []
        self.consecutive_spot_available = 0
        self.consecutive_spot_unavailable = 0
        self.last_decision = ClusterType.NONE
        self.work_segments = []
        self.spot_usage_pattern = []
        self.emergency_mode = False
        
        # Configuration
        self.safety_margin = 0.1  # 10% safety margin
        self.min_spot_run = 5  # minimum seconds to consider using spot
        self.aggressiveness = 0.7  # 0-1, higher = more aggressive spot usage
        
    def solve(self, spec_path: str) -> "Solution":
        # Read configuration if spec file exists
        if os.path.exists(spec_path):
            try:
                with open(spec_path, 'r') as f:
                    config = json.load(f)
                    # Could load custom parameters here
                    pass
            except:
                pass
                
        # Initialize remaining work and time
        self.remaining_work = self.task_duration
        self.remaining_time = self.deadline
        self.work_segments = []
        self.spot_usage_pattern = []
        
        return self
    
    def _calculate_criticality(self, elapsed: float, work_done: float) -> float:
        """Calculate how critical the situation is (0-1)"""
        total_work = self.task_duration
        total_time = self.deadline
        
        work_remaining = total_work - work_done
        time_remaining = total_time - elapsed
        
        if time_remaining <= 0 or work_remaining <= 0:
            return 1.0
            
        # Required work rate to finish on time
        required_rate = work_remaining / time_remaining
        
        # Normal rate (1 work per second when running)
        normal_rate = 1.0
        
        # Criticality increases as required rate approaches or exceeds normal rate
        criticality = min(1.0, max(0.0, (required_rate - normal_rate * 0.5) / (normal_rate * 0.5)))
        
        # Adjust for safety margin
        adjusted_time = time_remaining * (1 - self.safety_margin)
        if adjusted_time > 0:
            adjusted_required_rate = work_remaining / adjusted_time
            if adjusted_required_rate > normal_rate:
                criticality = 1.0
                
        return criticality
    
    def _should_use_spot(self, has_spot: bool, criticality: float, 
                         elapsed: float, work_done: float) -> bool:
        """Decide whether to use spot instances"""
        
        # Never use spot if not available
        if not has_spot:
            return False
            
        # Emergency mode - use OD only
        if self.emergency_mode:
            return False
            
        # High criticality - prefer OD
        if criticality > 0.8:
            return False
            
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - elapsed
        
        # If we have plenty of time, use spot
        if time_remaining > work_remaining * 2:  # 2x slack
            return True
            
        # Calculate if we can afford spot interruptions
        max_possible_interruptions = (time_remaining - work_remaining) / self.overhead_seconds
        
        # Be more conservative as max possible interruptions decrease
        if max_possible_interruptions < 5:
            # Less than 5 possible interruptions remaining
            spot_probability = max(0.0, min(1.0, max_possible_interruptions / 10))
            return spot_probability > (1 - self.aggressiveness)
            
        # Normal operation - use spot based on aggressiveness
        return True
    
    def _calculate_required_od_time(self, elapsed: float, work_done: float) -> float:
        """Calculate minimum OD time needed to finish by deadline"""
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - elapsed
        
        if time_remaining <= 0:
            return work_remaining
            
        # If we use only OD from now on
        od_time_needed = work_remaining
        
        # Account for remaining time
        if od_time_needed > time_remaining:
            # We're already in trouble
            return od_time_needed
            
        # Conservative estimate: assume worst-case spot interruptions
        # Each spot segment might be interrupted with overhead
        available_time = time_remaining
        od_required = max(0, work_remaining - available_time + self.overhead_seconds * 3)
        
        return od_required
    
    def _update_spot_history(self, has_spot: bool):
        """Update spot availability history"""
        self.spot_availability_history.append(1 if has_spot else 0)
        if len(self.spot_availability_history) > 100:
            self.spot_availability_history.pop(0)
            
        if has_spot:
            self.consecutive_spot_available += 1
            self.consecutive_spot_unavailable = 0
        else:
            self.consecutive_spot_unavailable += 1
            self.consecutive_spot_available = 0
            
        # Detect emergency if spot is consistently unavailable
        if self.consecutive_spot_unavailable > 30:  # ~30 seconds of no spot
            self.emergency_mode = True
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update state
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time) if self.task_done_time else 0
        self.remaining_work = self.task_duration - work_done
        self.remaining_time = self.deadline - elapsed
        
        # Update spot history
        self._update_spot_history(has_spot)
        
        # Update overhead state
        if self.in_overhead:
            self.overhead_remaining -= self.env.gap_seconds
            if self.overhead_remaining <= 0:
                self.in_overhead = False
                self.overhead_remaining = 0
                
        # Apply overhead if switching from SPOT to something else (interruption)
        if (last_cluster_type == ClusterType.SPOT and 
            self.env.cluster_type != ClusterType.SPOT and
            not self.in_overhead):
            self.in_overhead = True
            self.overhead_remaining = self.restart_overhead
            
        # If in overhead period, do nothing
        if self.in_overhead:
            self.last_decision = ClusterType.NONE
            return ClusterType.NONE
            
        # Calculate criticality
        criticality = self._calculate_criticality(elapsed, work_done)
        
        # Check if we're in emergency mode
        required_od_time = self._calculate_required_od_time(elapsed, work_done)
        if required_od_time > self.remaining_time * 0.9:  # Need OD for >90% of remaining time
            self.emergency_mode = True
            
        # Decide based on strategy
        if self.emergency_mode:
            # Use OD to guarantee completion
            decision = ClusterType.ON_DEMAND
        elif self._should_use_spot(has_spot, criticality, elapsed, work_done):
            decision = ClusterType.SPOT
        elif criticality > 0.5:
            # Moderate to high criticality - use OD
            decision = ClusterType.ON_DEMAND
        else:
            # Low criticality, spot not available - wait
            decision = ClusterType.NONE
            
        # Record decision
        self.last_decision = decision
        
        return decision
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)