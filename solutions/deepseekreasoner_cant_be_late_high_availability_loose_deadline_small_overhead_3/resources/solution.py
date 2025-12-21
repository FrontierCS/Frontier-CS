import argparse
from dataclasses import dataclass
from typing import List, Optional
import math

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


@dataclass
class State:
    """Track progress and deadlines"""
    total_work_needed: float
    deadline: float
    restart_overhead: float
    spot_price: float = 0.97
    ondemand_price: float = 3.06
    time_step: float = 1.0
    
    def __post_init__(self):
        # Convert to hours for easier calculation (prices are per hour)
        self.total_work_needed_hours = self.total_work_needed / 3600
        self.deadline_hours = self.deadline / 3600
        self.restart_overhead_hours = self.restart_overhead / 3600
        self.time_step_hours = self.time_step / 3600


class Solution(Strategy):
    NAME = "adaptive_deadline_aware"
    
    def __init__(self, args=None):
        super().__init__(args)
        self.state: Optional[State] = None
        self.spot_available_history: List[bool] = []
        self.current_overhead_remaining = 0.0
        self.last_decision = ClusterType.NONE
        self.work_done = 0.0
        self.consecutive_spot_failures = 0
        self.max_consecutive_failures = 5
        
    def solve(self, spec_path: str) -> "Solution":
        # No need to read spec_path for this implementation
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize state on first call
        if self.state is None:
            self.state = State(
                total_work_needed=self.task_duration,
                deadline=self.deadline,
                restart_overhead=self.restart_overhead,
                time_step=self.env.gap_seconds
            )
        
        current_time_hours = self.env.elapsed_seconds / 3600
        self.spot_available_history.append(has_spot)
        
        # Update work done
        if last_cluster_type == ClusterType.SPOT and has_spot:
            self.work_done += self.env.gap_seconds
            self.consecutive_spot_failures = 0
        elif last_cluster_type == ClusterType.ON_DEMAND:
            self.work_done += self.env.gap_seconds
            self.consecutive_spot_failures = 0
        elif last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_spot_failures += 1
        
        # Calculate remaining work and time
        remaining_work_hours = self.state.total_work_needed_hours - (self.work_done / 3600)
        remaining_time_hours = self.state.deadline_hours - current_time_hours
        
        # If work is done, do nothing
        if remaining_work_hours <= 0:
            return ClusterType.NONE
        
        # Calculate critical thresholds
        time_per_work_unit = self.state.time_step_hours
        
        # Conservative estimate: assume worst-case for spot
        min_time_to_finish = remaining_work_hours
        if has_spot:
            # Account for potential restarts
            conservative_factor = 1.2
            min_time_to_finish = remaining_work_hours * conservative_factor
        
        # Calculate urgency (0 = no urgency, 1 = critical)
        urgency = max(0.0, 1.0 - (remaining_time_hours / (min_time_to_finish * 1.5)))
        
        # Calculate safety margin
        safety_margin_hours = self.state.restart_overhead_hours * 3
        
        # Decision logic
        if remaining_time_hours <= safety_margin_hours:
            # Critical: must use on-demand to guarantee completion
            decision = ClusterType.ON_DEMAND
        
        elif urgency > 0.7:
            # High urgency: prefer on-demand
            if has_spot and self.consecutive_spot_failures < self.max_consecutive_failures:
                decision = ClusterType.SPOT
            else:
                decision = ClusterType.ON_DEMAND
        
        elif urgency > 0.4:
            # Medium urgency: use spot when available, otherwise on-demand
            if has_spot and self.consecutive_spot_failures < 2:
                decision = ClusterType.SPOT
            else:
                decision = ClusterType.ON_DEMAND
        
        else:
            # Low urgency: use spot when available, otherwise wait
            if has_spot:
                decision = ClusterType.SPOT
            else:
                # Check if we can afford to wait
                can_wait = remaining_time_hours > remaining_work_hours * 1.3
                if can_wait:
                    decision = ClusterType.NONE
                else:
                    decision = ClusterType.ON_DEMAND
        
        # Handle spot unavailability
        if decision == ClusterType.SPOT and not has_spot:
            # Fallback to on-demand if we're getting too many failures
            if self.consecutive_spot_failures >= self.max_consecutive_failures:
                decision = ClusterType.ON_DEMAND
            else:
                # Wait for spot to become available
                can_wait = remaining_time_hours > remaining_work_hours * 1.2
                decision = ClusterType.NONE if can_wait else ClusterType.ON_DEMAND
        
        self.last_decision = decision
        return decision
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
