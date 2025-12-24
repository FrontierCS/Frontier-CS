import argparse
import math
from enum import Enum
from typing import List, Optional, Tuple

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class State(Enum):
    IDLE = 0
    RUNNING_SPOT = 1
    RUNNING_OD = 2
    RESTARTING = 3


class Solution(Strategy):
    NAME = "adaptive_hedging"

    def __init__(self, args):
        super().__init__(args)
        self.spot_price = 0.97
        self.od_price = 3.06
        self.price_ratio = self.od_price / self.spot_price
        
        # State tracking
        self.state = State.IDLE
        self.restart_timer = 0.0
        self.work_done = 0.0
        self.time_elapsed = 0.0
        self.spot_availability_history = []
        self.last_decision = ClusterType.NONE
        
        # Adaptive parameters
        self.aggressiveness = 0.7  # Base spot usage aggressiveness
        self.safety_margin_factor = 1.2  # Safety margin for deadline
        self.min_spot_confidence = 0.3  # Minimum confidence to use spot

    def solve(self, spec_path: str) -> "Solution":
        # Parse configuration if needed
        try:
            with open(spec_path, 'r') as f:
                # Could parse additional config here
                pass
        except:
            pass
        return self

    def _update_state(self, last_cluster_type: ClusterType, has_spot: bool):
        """Update internal state based on last step results"""
        self.time_elapsed = self.env.elapsed_seconds
        self.work_done = sum(self.task_done_time) if self.task_done_time else 0.0
        
        # Update spot availability history (keep recent window)
        self.spot_availability_history.append(1 if has_spot else 0)
        if len(self.spot_availability_history) > 100:
            self.spot_availability_history.pop(0)
        
        # Update state machine
        if last_cluster_type == ClusterType.NONE:
            if self.state == State.RESTARTING:
                self.restart_timer -= self.env.gap_seconds
                if self.restart_timer <= 0:
                    self.state = State.IDLE
        elif last_cluster_type == ClusterType.SPOT:
            if has_spot:
                self.state = State.RUNNING_SPOT
            else:
                # Spot was preempted
                self.state = State.RESTARTING
                self.restart_timer = self.restart_overhead
        elif last_cluster_type == ClusterType.ON_DEMAND:
            self.state = State.RUNNING_OD
        
        self.last_decision = last_cluster_type

    def _calculate_spot_confidence(self) -> float:
        """Calculate confidence in spot availability based on history"""
        if not self.spot_availability_history:
            return 0.5
        
        recent_window = self.spot_availability_history[-20:] if len(self.spot_availability_history) >= 20 else self.spot_availability_history
        if not recent_window:
            return 0.5
        
        availability = sum(recent_window) / len(recent_window)
        
        # Apply some smoothing and bias toward recent observations
        weight = min(1.0, len(recent_window) / 20.0)
        confidence = 0.3 + 0.7 * availability * weight
        
        return max(self.min_spot_confidence, min(confidence, 0.95))

    def _calculate_safety_margin(self) -> float:
        """Calculate dynamic safety margin based on progress"""
        remaining_work = self.task_duration - self.work_done
        time_left = self.deadline - self.time_elapsed
        
        if remaining_work <= 0:
            return 0
        
        # Base required time (assuming OD)
        base_time = remaining_work
        
        # Add restart overhead estimate (worst case: 2 restarts)
        restart_estimate = 2 * self.restart_overhead
        
        # Total required time with safety
        required = base_time + restart_estimate
        
        # Calculate urgency factor (0-1, higher means more urgent)
        urgency = 1.0 - (time_left - required) / (self.deadline * 0.5)
        urgency = max(0.0, min(1.0, urgency))
        
        # Adjust safety margin based on urgency
        margin_factor = self.safety_margin_factor * (1.0 + 0.5 * urgency)
        
        return required * margin_factor

    def _should_use_spot(self, has_spot: bool) -> bool:
        """Determine if we should use spot in current conditions"""
        if not has_spot:
            return False
        
        remaining_work = self.task_duration - self.work_done
        time_left = self.deadline - self.time_elapsed
        
        if remaining_work <= 0:
            return False
        
        # If we're in restart mode, don't start spot
        if self.state == State.RESTARTING:
            return False
        
        spot_confidence = self._calculate_spot_confidence()
        safety_margin = self._calculate_safety_margin()
        
        # Calculate expected spot efficiency considering restarts
        expected_spot_efficiency = spot_confidence * (1.0 - 0.1)  # 10% penalty for potential restarts
        
        # Calculate time needed with spot vs OD
        time_needed_spot = remaining_work / expected_spot_efficiency
        time_needed_od = remaining_work
        
        # Check if we have enough time for spot
        has_time_for_spot = time_left >= time_needed_spot * self.safety_margin_factor
        
        # Check if we're running late
        is_running_late = time_left < safety_margin
        
        # Aggressiveness adjustment based on progress
        progress_ratio = self.work_done / self.task_duration
        time_ratio = self.time_elapsed / self.deadline
        
        if progress_ratio < time_ratio:  # Behind schedule
            current_aggressiveness = self.aggressiveness * 0.8
        else:  # Ahead of schedule
            current_aggressiveness = self.aggressiveness * 1.2
        
        # Decide based on multiple factors
        use_spot = (
            has_spot and
            has_time_for_spot and
            not is_running_late and
            spot_confidence > self.min_spot_confidence and
            (expected_spot_efficiency > 0.7 or time_left > safety_margin * 1.5) and
            current_aggressiveness > 0.5
        )
        
        return use_spot

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update internal state
        self._update_state(last_cluster_type, has_spot)
        
        remaining_work = self.task_duration - self.work_done
        time_left = self.deadline - self.time_elapsed
        
        # If work is done or deadline passed, do nothing
        if remaining_work <= 0 or time_left <= 0:
            return ClusterType.NONE
        
        # If we're in restart mode, wait
        if self.state == State.RESTARTING:
            return ClusterType.NONE
        
        # Check if we're running out of time
        safety_margin = self._calculate_safety_margin()
        is_critical = time_left < safety_margin * 1.1
        
        # Critical path: use OD if behind schedule
        if is_critical:
            # Calculate if we can still make it with OD
            time_needed_od = remaining_work
            if time_left >= time_needed_od:
                return ClusterType.ON_DEMAND
            else:
                # Too late, but try anyway
                return ClusterType.ON_DEMAND
        
        # Try to use spot if available and conditions are good
        if self._should_use_spot(has_spot):
            return ClusterType.SPOT
        
        # If spot not available or not confident, use OD if we need to make progress
        if remaining_work > 0 and time_left > 0:
            # Check if we should pause or use OD
            progress_rate = self.work_done / max(1.0, self.time_elapsed)
            required_progress_rate = remaining_work / time_left
            
            if progress_rate >= required_progress_rate * 0.9:
                # We're on track, can afford to wait for spot
                return ClusterType.NONE
            else:
                # Falling behind, use OD
                return ClusterType.ON_DEMAND
        
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
