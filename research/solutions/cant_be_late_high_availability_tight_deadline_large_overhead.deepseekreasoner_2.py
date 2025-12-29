import json
import math
from typing import Dict, List, Optional, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.spec_config = None
        self.spot_price = 0.0
        self.on_demand_price = 0.0
        self.task_duration_seconds = 0
        self.deadline_seconds = 0
        self.restart_overhead_seconds = 0
        self.slack_seconds = 0
        
        # State tracking
        self.work_done = 0.0
        self.time_elapsed = 0.0
        self.spot_available_history = []
        self.last_decision = ClusterType.NONE
        self.restart_timer = 0.0
        self.consecutive_spot_failures = 0
        self.safety_margin = 0.0
        self.spot_availability_rate = 0.7  # Default estimate
        
    def solve(self, spec_path: str) -> "Solution":
        """Load configuration from spec file"""
        try:
            with open(spec_path, 'r') as f:
                self.spec_config = json.load(f)
                
            # Extract key parameters
            self.task_duration_seconds = self.task_duration
            self.deadline_seconds = self.deadline
            self.restart_overhead_seconds = self.restart_overhead
            
            # Calculate slack (deadline - task_duration)
            self.slack_seconds = self.deadline_seconds - self.task_duration_seconds
            
            # Set conservative safety margin (50% of slack)
            self.safety_margin = self.slack_seconds * 0.5
            
            # Initialize state
            self.work_done = 0.0
            self.time_elapsed = 0.0
            self.spot_available_history = []
            self.last_decision = ClusterType.NONE
            self.restart_timer = 0.0
            self.consecutive_spot_failures = 0
            
        except Exception:
            # If spec file reading fails, use defaults
            self.task_duration_seconds = 48 * 3600  # 48 hours
            self.deadline_seconds = 52 * 3600  # 52 hours
            self.restart_overhead_seconds = 0.2 * 3600  # 0.2 hours
            self.slack_seconds = 4 * 3600  # 4 hours
            self.safety_margin = 2 * 3600  # 2 hours
            
        return self
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """Decision logic for each time step"""
        
        # Update internal state
        self.time_elapsed = self.env.elapsed_seconds
        time_step = self.env.gap_seconds
        
        # Track spot availability history
        self.spot_available_history.append(has_spot)
        if len(self.spot_available_history) > 100:
            self.spot_available_history.pop(0)
            
        # Update work done
        if last_cluster_type != ClusterType.NONE and self.restart_timer <= 0:
            work_this_step = time_step
            self.work_done += work_this_step
            
        # Update restart timer
        if self.restart_timer > 0:
            self.restart_timer = max(0, self.restart_timer - time_step)
            
        # Calculate progress metrics
        work_remaining = max(0, self.task_duration_seconds - self.work_done)
        time_remaining = max(0, self.deadline_seconds - self.time_elapsed)
        
        # Calculate required productivity rate
        if time_remaining > 0:
            required_rate = work_remaining / time_remaining
        else:
            required_rate = float('inf')
            
        # Check if we're behind schedule
        is_behind = work_remaining > 0 and (
            time_remaining < work_remaining + self.restart_overhead_seconds + self.safety_margin
        )
        
        # Handle restart logic
        if last_cluster_type == ClusterType.NONE and self.last_decision != ClusterType.NONE:
            # Just completed a restart
            self.restart_timer = 0
        elif self.last_decision != last_cluster_type and last_cluster_type != ClusterType.NONE:
            # Starting a new instance - set restart timer
            self.restart_timer = self.restart_overhead_seconds
            
        # Decision logic
        decision = self._make_decision(
            has_spot=has_spot,
            is_behind=is_behind,
            work_remaining=work_remaining,
            time_remaining=time_remaining,
            required_rate=required_rate,
            last_cluster_type=last_cluster_type
        )
        
        # Update consecutive spot failures counter
        if decision == ClusterType.SPOT and not has_spot:
            # This shouldn't happen if _make_decision is correct, but as safety
            decision = ClusterType.ON_DEMAND if is_behind else ClusterType.NONE
            
        if decision == ClusterType.SPOT and has_spot:
            self.consecutive_spot_failures = 0
        elif decision == ClusterType.SPOT and not has_spot:
            self.consecutive_spot_failures += 1
        elif decision != ClusterType.SPOT:
            self.consecutive_spot_failures = 0
            
        # Store last decision for next iteration
        self.last_decision = decision
        
        return decision
    
    def _make_decision(self, has_spot: bool, is_behind: bool, work_remaining: float,
                      time_remaining: float, required_rate: float, 
                      last_cluster_type: ClusterType) -> ClusterType:
        """Core decision-making logic"""
        
        # If we're in a restart, continue with NONE
        if self.restart_timer > 0:
            return ClusterType.NONE
            
        # Emergency: if we're very behind, use on-demand
        if is_behind and time_remaining < work_remaining + self.restart_overhead_seconds:
            return ClusterType.ON_DEMAND
            
        # If we're behind schedule, be more aggressive
        if is_behind:
            if has_spot:
                # Try spot first when behind but with time buffer
                return ClusterType.SPOT
            else:
                # No spot available, use on-demand
                return ClusterType.ON_DEMAND
                
        # Not behind schedule - be cost-conscious
        if has_spot:
            # Use spot when available and we're not in a rush
            return ClusterType.SPOT
        else:
            # No spot available - pause to save cost if we have time
            if time_remaining > work_remaining + self.restart_overhead_seconds + self.safety_margin * 0.5:
                return ClusterType.NONE
            else:
                # Getting tight, use on-demand
                return ClusterType.ON_DEMAND