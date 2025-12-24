import math
import random
from enum import Enum
from typing import List, Tuple

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except ImportError:
    # For local testing if imports fail
    class ClusterType(Enum):
        SPOT = "SPOT"
        ON_DEMAND = "ON_DEMAND"
        NONE = "NONE"

    class Strategy:
        pass


class Solution(Strategy):
    NAME = "adaptive_hedge"

    def __init__(self, args=None):
        super().__init__(args)
        self.spot_price = 0.97
        self.ondemand_price = 3.06
        self.price_ratio = self.spot_price / self.ondemand_price
        self.restart_cost_hours = 0.2
        self.safety_margin_hours = 1.0
        
        # State tracking
        self.consecutive_spot_uptime = 0
        self.spot_available_history = []
        self.work_remaining_history = []
        self.time_remaining_history = []
        self.decision_history = []
        self.initial_total_work = None

    def solve(self, spec_path: str) -> "Solution":
        # Reset state for new run
        self.consecutive_spot_uptime = 0
        self.spot_available_history = []
        self.work_remaining_history = []
        self.time_remaining_history = []
        self.decision_history = []
        self.initial_total_work = None
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize on first call
        if self.initial_total_work is None:
            self.initial_total_work = self.task_duration
        
        # Update consecutive spot uptime counter
        if last_cluster_type == ClusterType.SPOT:
            self.consecutive_spot_uptime += 1
        else:
            self.consecutive_spot_uptime = 0
        
        # Calculate current state
        work_done = sum(self.task_done_time) if self.task_done_time else 0
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        # Convert to hours for easier reasoning
        work_remaining_hours = work_remaining / 3600
        time_remaining_hours = time_remaining / 3600
        
        # Store history for trend analysis
        self.spot_available_history.append(has_spot)
        self.work_remaining_history.append(work_remaining_hours)
        self.time_remaining_history.append(time_remaining_hours)
        
        # Emergency mode: must use on-demand to meet deadline
        if time_remaining_hours <= work_remaining_hours + 0.1:  # Very tight
            self.decision_history.append(ClusterType.ON_DEMAND)
            return ClusterType.ON_DEMAND
        
        # Critical mode: insufficient slack
        if time_remaining_hours <= work_remaining_hours + self.safety_margin_hours:
            # Use on-demand unless spot is available AND we have good uptime
            if (has_spot and self.consecutive_spot_uptime > 5 and 
                random.random() < 0.3):  # 30% chance to risk spot
                self.decision_history.append(ClusterType.SPOT)
                return ClusterType.SPOT
            self.decision_history.append(ClusterType.ON_DEMAND)
            return ClusterType.ON_DEMAND
        
        # Normal operation: balance risk vs reward
        if not has_spot:
            # No spot available
            if time_remaining_hours > work_remaining_hours + 2.0:
                # Enough slack to wait
                self.decision_history.append(ClusterType.NONE)
                return ClusterType.NONE
            else:
                # Use on-demand to make progress
                self.decision_history.append(ClusterType.ON_DEMAND)
                return ClusterType.ON_DEMAND
        
        # Spot is available - decide whether to use it
        # Calculate risk-adjusted value
        expected_spot_uptime = self.estimate_spot_uptime()
        restart_penalty = self.restart_cost_hours / expected_spot_uptime if expected_spot_uptime > 0 else 1.0
        
        # Effective cost ratio including restart risk
        effective_ratio = self.price_ratio * (1 + restart_penalty)
        
        # Decision threshold based on slack
        slack_ratio = (time_remaining_hours - work_remaining_hours) / work_remaining_hours
        
        # Adaptive threshold: more aggressive with more slack
        if slack_ratio > 0.15:  # Good slack (>7.2 hours for 48h work)
            threshold = 0.85
        elif slack_ratio > 0.083:  # Moderate slack (>4 hours)
            threshold = 0.70
        else:
            threshold = 0.55
        
        # Use spot if it's sufficiently valuable
        if effective_ratio < threshold:
            self.decision_history.append(ClusterType.SPOT)
            return ClusterType.SPOT
        
        # Otherwise use on-demand or wait
        if slack_ratio > 0.1 and random.random() < 0.5:
            # Wait for potentially better conditions
            self.decision_history.append(ClusterType.NONE)
            return ClusterType.NONE
        
        self.decision_history.append(ClusterType.ON_DEMAND)
        return ClusterType.ON_DEMAND
    
    def estimate_spot_uptime(self) -> float:
        """Estimate expected spot uptime in hours based on recent history."""
        if len(self.spot_available_history) < 10:
            return 2.0  # Default assumption
        
        # Look at recent spot availability pattern
        recent = self.spot_available_history[-20:] if len(self.spot_available_history) >= 20 else self.spot_available_history
        
        # Calculate availability rate
        available_count = sum(recent)
        availability_rate = available_count / len(recent) if recent else 0.5
        
        # Base estimate on availability rate (hours)
        # Low availability regions: 4-40% -> 0.1 to 4 hours expected uptime
        min_uptime = 0.1
        max_uptime = 4.0
        base_uptime = min_uptime + availability_rate * (max_uptime - min_uptime)
        
        # Adjust based on current consecutive uptime
        if self.consecutive_spot_uptime > 0:
            # If already running on spot, expect longer uptime
            adjustment = min(2.0, self.consecutive_spot_uptime * 0.1)
            return base_uptime * adjustment
        
        return base_uptime

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
