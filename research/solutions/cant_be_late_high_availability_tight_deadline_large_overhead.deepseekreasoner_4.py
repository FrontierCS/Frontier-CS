import numpy as np
from enum import Enum
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class State(Enum):
    START = 0
    SPOT_RUNNING = 1
    SPOT_GAP = 2
    OD_RUNNING = 3

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__()
        self.args = args
        self.state = State.START
        self.spot_unavailable_time = 0
        self.consecutive_spot_failures = 0
        self.last_spot_check = 0
        self.work_done = 0
        self.last_progress = 0
        self.steps_in_current_state = 0
        self.initial_slack = None
        self.spot_available_history = []

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_time = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        # Track spot availability history
        self.spot_available_history.append(1 if has_spot else 0)
        if len(self.spot_available_history) > 100:
            self.spot_available_history.pop(0)
        
        # Calculate current progress
        current_progress = sum(self.task_done_time)
        progress_made = current_progress - self.last_progress
        self.last_progress = current_progress
        
        # Update state based on progress
        if progress_made > 0:
            self.work_done += progress_made
        
        # Calculate time remaining until deadline
        time_remaining = self.deadline - current_time
        work_remaining = self.task_duration - current_progress
        
        # Initialize slack on first call
        if self.initial_slack is None:
            self.initial_slack = self.deadline - self.task_duration
        
        # State machine transitions
        self.steps_in_current_state += 1
        
        if self.state == State.START:
            if has_spot:
                self.state = State.SPOT_RUNNING
                return ClusterType.SPOT
            else:
                # If no spot at start, use OD for initial work
                if work_remaining > 0.3 * self.task_duration:
                    self.state = State.OD_RUNNING
                    return ClusterType.ON_DEMAND
                return ClusterType.NONE
        
        elif self.state == State.SPOT_RUNNING:
            if not has_spot:
                self.consecutive_spot_failures += 1
                self.spot_unavailable_time = current_time
                self.state = State.SPOT_GAP
                return ClusterType.NONE
            
            self.consecutive_spot_failures = 0
            
            # Calculate if we should switch to OD to meet deadline
            time_needed_with_restart = work_remaining
            if time_needed_with_restart > time_remaining - self.restart_overhead:
                self.state = State.OD_RUNNING
                return ClusterType.ON_DEMAND
            
            # If we've been running spot for a while successfully, continue
            return ClusterType.SPOT
        
        elif self.state == State.SPOT_GAP:
            time_in_gap = current_time - self.spot_unavailable_time
            
            # If we've waited too long for spot, consider OD
            max_wait_time = min(3600, time_remaining * 0.2)
            
            if time_in_gap > max_wait_time or work_remaining > time_remaining * 0.8:
                self.state = State.OD_RUNNING
                return ClusterType.ON_DEMAND
            
            # Return to spot if available
            if has_spot:
                spot_success_rate = np.mean(self.spot_available_history) if self.spot_available_history else 0
                
                # Only return to spot if success rate is reasonable
                if spot_success_rate > 0.4 or time_remaining > work_remaining * 1.5:
                    self.state = State.SPOT_RUNNING
                    return ClusterType.SPOT
            
            return ClusterType.NONE
        
        elif self.state == State.OD_RUNNING:
            # Check if we can switch back to spot
            if has_spot:
                # Calculate if we have enough time to use spot
                spot_time_needed = work_remaining
                current_slack = time_remaining - spot_time_needed
                
                # Only switch if we have sufficient slack
                min_slack_for_switch = max(self.restart_overhead * 2, self.initial_slack * 0.3)
                
                if current_slack > min_slack_for_switch and work_remaining > self.task_duration * 0.1:
                    spot_success_rate = np.mean(self.spot_available_history) if self.spot_available_history else 0
                    
                    # Be more aggressive with spot if success rate is high
                    if spot_success_rate > 0.5:
                        self.state = State.SPOT_RUNNING
                        return ClusterType.SPOT
            
            return ClusterType.ON_DEMAND
        
        # Default fallback
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)