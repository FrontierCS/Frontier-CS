import argparse
import math
from enum import Enum
from typing import List, Optional, Tuple
from dataclasses import dataclass
from collections import deque

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class InstanceState(Enum):
    """Track the state of spot instance usage."""
    IDLE = 0
    RUNNING = 1
    RESTARTING = 2


@dataclass
class SpotWindow:
    """Track continuous availability windows for spot instances."""
    start: float
    end: float
    duration: float


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__()
        self.args = args
        self.spot_price = 0.97  # $/hr
        self.ondemand_price = 3.06  # $/hr
        self.restart_overhead_hrs = 0.05  # hours
        self.restart_overhead_sec = 180  # seconds
        self.task_duration_hrs = 48
        self.deadline_hrs = 52
        self.slack_hrs = 4
        
        # State tracking
        self.spot_windows: List[SpotWindow] = []
        self.spot_availability: List[bool] = []
        self.spot_unavailable_times: List[float] = []
        self.spot_state = InstanceState.IDLE
        self.spot_restart_remaining = 0
        self.remaining_work = 0.0
        self.total_cost = 0.0
        self.initialized = False
        
        # Predictive parameters
        self.min_safe_window = 1.0  # minimum window size to consider using spot (hours)
        self.emergency_threshold = 2.0  # hours before deadline to switch to on-demand
        self.spot_usage_threshold = 0.3  # minimum spot availability to consider using spot
        self.prediction_horizon = 24  # hours to look ahead for predictions

    def solve(self, spec_path: str) -> "Solution":
        """Optional initialization."""
        # Read configuration if spec_path exists
        # For now, just return self
        return self

    def _initialize_state(self, task_duration: float, deadline: float) -> None:
        """Initialize state variables."""
        self.remaining_work = task_duration / 3600.0  # Convert to hours
        self.spot_windows = []
        self.spot_availability = []
        self.spot_unavailable_times = []
        self.spot_state = InstanceState.IDLE
        self.spot_restart_remaining = 0
        self.total_cost = 0.0
        self.initialized = True

    def _update_spot_windows(self, has_spot: bool, current_time: float) -> None:
        """Update spot availability windows."""
        self.spot_availability.append(has_spot)
        
        if not self.spot_windows:
            if has_spot:
                self.spot_windows.append(SpotWindow(current_time, float('inf'), 0))
        else:
            current_window = self.spot_windows[-1]
            if has_spot and current_window.end == float('inf'):
                # Still in same window
                pass
            elif not has_spot and current_window.end == float('inf'):
                # Window just ended
                current_window.end = current_time
                current_window.duration = (current_time - current_window.start) / 3600.0
            elif has_spot and current_window.end < float('inf'):
                # New window starting
                self.spot_windows.append(SpotWindow(current_time, float('inf'), 0))
            elif not has_spot:
                # Record unavailable time
                if not self.spot_unavailable_times or self.spot_unavailable_times[-1] != current_time:
                    self.spot_unavailable_times.append(current_time)

    def _predict_spot_availability(self, current_time: float, horizon_hours: float) -> Tuple[float, float]:
        """
        Predict spot availability in the near future.
        Returns: (available_fraction, expected_window_size)
        """
        if len(self.spot_availability) < 10:
            # Not enough data, assume average
            return 0.6, 2.0  # Conservative estimate
        
        # Look at recent history to predict near future
        lookback = min(100, len(self.spot_availability))
        recent = self.spot_availability[-lookback:]
        recent_available = sum(recent) / len(recent)
        
        # If we have window data, use it for prediction
        if self.spot_windows:
            recent_windows = [w for w in self.spot_windows if w.duration > 0]
            if recent_windows:
                avg_window = sum(w.duration for w in recent_windows) / len(recent_windows)
                return recent_available, avg_window
        
        return recent_available, 1.0  # Default 1 hour window

    def _calculate_time_pressure(self, current_time: float) -> float:
        """Calculate time pressure factor (0-1, higher means more pressure)."""
        elapsed_hours = current_time / 3600.0
        remaining_time = self.deadline_hrs - elapsed_hours
        required_work = self.remaining_work
        
        if required_work <= 0:
            return 0.0
        
        # Time pressure = work remaining / time remaining
        pressure = required_work / max(0.1, remaining_time)
        
        # Normalize to 0-1 range (but allow >1 for emergency)
        return pressure

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """Decision logic for each time step."""
        current_time = self.env.elapsed_seconds
        time_step_hours = self.env.gap_seconds / 3600.0
        
        # Initialize on first call
        if not self.initialized:
            self._initialize_state(self.task_duration, self.deadline)
        
        # Update spot availability tracking
        self._update_spot_windows(has_spot, current_time)
        
        # Update remaining work based on last step
        if last_cluster_type == ClusterType.SPOT and has_spot and self.spot_state == InstanceState.RUNNING:
            # Spot was running and available
            work_done = time_step_hours
            self.remaining_work = max(0, self.remaining_work - work_done)
            self.total_cost += work_done * self.spot_price
            self.spot_state = InstanceState.RUNNING
        elif last_cluster_type == ClusterType.ON_DEMAND:
            # On-demand was running
            work_done = time_step_hours
            self.remaining_work = max(0, self.remaining_work - work_done)
            self.total_cost += work_done * self.ondemand_price
            self.spot_state = InstanceState.IDLE
            self.spot_restart_remaining = 0
        elif last_cluster_type == ClusterType.NONE:
            # Nothing was running
            self.spot_state = InstanceState.IDLE
            if self.spot_restart_remaining > 0:
                self.spot_restart_remaining = max(0, self.spot_restart_remaining - time_step_hours)
        
        # Handle spot restart state
        if self.spot_state == InstanceState.RESTARTING:
            self.spot_restart_remaining = max(0, self.spot_restart_remaining - time_step_hours)
            if self.spot_restart_remaining <= 0:
                self.spot_state = InstanceState.IDLE
        
        # Check if completed
        if self.remaining_work <= 0:
            return ClusterType.NONE
        
        # Calculate time pressure
        time_pressure = self._calculate_time_pressure(current_time)
        elapsed_hours = current_time / 3600.0
        remaining_time = self.deadline_hrs - elapsed_hours
        
        # Emergency mode: switch to on-demand if we're running out of time
        if remaining_time <= self.emergency_threshold:
            if self.remaining_work > 0:
                # Use on-demand to guarantee completion
                return ClusterType.ON_DEMAND
        
        # Calculate cost-benefit of using spot
        if has_spot and self.spot_restart_remaining <= 0:
            # Predict future spot availability
            avail_fraction, expected_window = self._predict_spot_availability(
                current_time, self.prediction_horizon
            )
            
            # Calculate expected cost of using spot vs on-demand
            spot_cost_per_hour = self.spot_price
            ondemand_cost_per_hour = self.ondemand_price
            
            # Factor in restart overhead cost
            restart_cost_hours = self.restart_overhead_hrs * ondemand_cost_per_hour
            expected_interruptions = max(0, (self.remaining_work / max(0.1, expected_window)) - 1)
            expected_restart_cost = expected_interruptions * restart_cost_hours
            
            total_spot_cost = (self.remaining_work * spot_cost_per_hour) + expected_restart_cost
            total_ondemand_cost = self.remaining_work * ondemand_cost_per_hour
            
            # Decide based on cost and time pressure
            cost_saving = total_ondemand_cost - total_spot_cost
            cost_saving_ratio = cost_saving / max(1, total_ondemand_cost)
            
            # Use spot if:
            # 1. We expect cost savings
            # 2. The expected window is large enough
            # 3. Time pressure is not too high
            use_spot = (
                cost_saving_ratio > 0.1 and
                expected_window >= self.min_safe_window and
                time_pressure < 1.5 and
                avail_fraction >= self.spot_usage_threshold
            )
            
            if use_spot:
                # Start spot with restart overhead
                if self.spot_state == InstanceState.IDLE:
                    self.spot_state = InstanceState.RESTARTING
                    self.spot_restart_remaining = self.restart_overhead_hrs
                    # Pay for restart time (approximated as on-demand cost)
                    self.total_cost += self.restart_overhead_hrs * ondemand_cost_per_hour
                return ClusterType.SPOT
        
        # Default to on-demand if spot is not available or not worthwhile
        if self.remaining_work > 0 and time_pressure > 0.8:
            return ClusterType.ON_DEMAND
        
        # Wait if we have time and spot might become available
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)