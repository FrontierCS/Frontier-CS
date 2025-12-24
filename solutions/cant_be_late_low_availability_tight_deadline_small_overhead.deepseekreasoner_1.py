import os
import pickle
import random
import numpy as np
from typing import Dict, List, Tuple, Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType
import argparse

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.spec = None
        self.spot_trace = None
        self.cost_spot = 0.97
        self.cost_ondemand = 3.06
        self.work_remaining = None
        self.time_remaining = None
        self.safety_margin = 3600  # 1 hour safety margin
        self.conservative_threshold = 7200  # 2 hours threshold for conservative mode
        self.aggressive_window = 21600  # 6 hours window for aggressive spot usage
        self.restart_penalty = 180  # 3 minutes in seconds
        self.spot_availability_history = []
        self.consecutive_spot_failures = 0
        self.last_decision = None
        self.conservative_mode = False
        self.spot_availability_rate = 0.0
        
    def solve(self, spec_path: str) -> "Solution":
        """Read specification file if needed."""
        if os.path.exists(spec_path):
            try:
                with open(spec_path, 'rb') as f:
                    self.spec = pickle.load(f)
            except:
                pass
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """Decision logic for each time step."""
        current_time = self.env.elapsed_seconds
        step_size = self.env.gap_seconds
        
        # Update spot availability history
        self.spot_availability_history.append(1 if has_spot else 0)
        if len(self.spot_availability_history) > 100:
            self.spot_availability_history.pop(0)
        
        # Calculate current spot availability rate
        if self.spot_availability_history:
            self.spot_availability_rate = sum(self.spot_availability_history) / len(self.spot_availability_history)
        
        # Update consecutive spot failures
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_spot_failures += 1
        else:
            self.consecutive_spot_failures = 0
        
        # Calculate remaining work and time
        if self.task_done_time:
            completed_work = sum(segment[1] - segment[0] for segment in self.task_done_time)
        else:
            completed_work = 0
        
        self.work_remaining = self.task_duration - completed_work
        self.time_remaining = self.deadline - current_time
        
        # Calculate effective work rate needed
        effective_time_needed = self.work_remaining
        if last_cluster_type == ClusterType.NONE:
            effective_time_needed += self.restart_overhead
        
        # Determine if we're in critical zone
        time_critical = self.time_remaining < effective_time_needed + self.safety_margin
        very_critical = self.time_remaining < effective_time_needed + (self.restart_overhead * 2)
        
        # Switch to conservative mode if conditions warrant
        if (time_critical or 
            self.consecutive_spot_failures >= 3 or
            self.spot_availability_rate < 0.2):
            self.conservative_mode = True
        elif not time_critical and self.spot_availability_rate > 0.5:
            self.conservative_mode = False
        
        # Decision logic
        if very_critical:
            # Use on-demand when very critical
            decision = ClusterType.ON_DEMAND
        
        elif self.conservative_mode:
            # Conservative mode: use spot only when very safe
            if (has_spot and 
                self.time_remaining > effective_time_needed + self.conservative_threshold and
                self.spot_availability_rate > 0.4):
                decision = ClusterType.SPOT
            else:
                decision = ClusterType.ON_DEMAND
        
        else:
            # Aggressive mode: prefer spot when available
            if has_spot:
                # Check if we have enough time buffer for spot usage
                time_buffer_needed = effective_time_needed * (1.0 / self.spot_availability_rate if self.spot_availability_rate > 0 else 2.0)
                
                if self.time_remaining > time_buffer_needed + self.restart_overhead:
                    decision = ClusterType.SPOT
                else:
                    decision = ClusterType.ON_DEMAND
            else:
                # No spot available
                if time_critical:
                    decision = ClusterType.ON_DEMAND
                else:
                    # Wait for spot to become available if we have time
                    if self.time_remaining > effective_time_needed + 3600:  # 1 hour buffer
                        decision = ClusterType.NONE
                    else:
                        decision = ClusterType.ON_DEMAND
        
        # Ensure we don't return SPOT when spot is not available
        if decision == ClusterType.SPOT and not has_spot:
            if time_critical:
                decision = ClusterType.ON_DEMAND
            else:
                decision = ClusterType.NONE
        
        # Store last decision
        self.last_decision = decision
        
        return decision

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
