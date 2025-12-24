import argparse
import json
from enum import Enum
from typing import List, Dict, Tuple
import math
import random

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args=None):
        super().__init__(args)
        self.config = {}
        self.remaining_work = 0.0
        self.time_elapsed = 0.0
        self.deadline = 0.0
        self.restart_overhead = 0.0
        self.gap_seconds = 1.0
        self.spot_price = 0.0
        self.od_price = 0.0
        self.in_restart = False
        self.restart_timer = 0.0
        self.last_decision = ClusterType.NONE
        self.work_done = 0.0
        self.spot_history = []
        self.spot_availability = 0.0
        self.safety_margin = 0.0
        
    def solve(self, spec_path: str) -> "Solution":
        try:
            with open(spec_path, 'r') as f:
                self.config = json.load(f)
        except:
            self.config = {}
        
        # Default parameters based on problem description
        self.spot_price = self.config.get('spot_price', 0.97)  # $/hr
        self.od_price = self.config.get('od_price', 3.06)  # $/hr
        self.safety_margin = self.config.get('safety_margin', 0.5)  # hours
        
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update internal state from environment
        self.time_elapsed = self.env.elapsed_seconds
        self.gap_seconds = self.env.gap_seconds
        self.remaining_work = self.task_duration - sum(self.task_done_time)
        self.deadline = self.deadline
        self.restart_overhead = self.restart_overhead
        
        # Update spot availability history
        self.spot_history.append(1 if has_spot else 0)
        if len(self.spot_history) > 100:
            self.spot_history.pop(0)
        
        # Calculate current spot availability (recent window)
        if len(self.spot_history) > 0:
            self.spot_availability = sum(self.spot_history) / len(self.spot_history)
        
        # Update restart timer
        if self.in_restart:
            self.restart_timer -= self.gap_seconds
            if self.restart_timer <= 0:
                self.in_restart = False
        
        # If in restart, wait (use NONE)
        if self.in_restart:
            self.last_decision = ClusterType.NONE
            return ClusterType.NONE
        
        # Check if we need to restart (spot was used but now unavailable)
        if (last_cluster_type == ClusterType.SPOT and 
            self.env.cluster_type == ClusterType.SPOT and 
            not has_spot):
            self.in_restart = True
            self.restart_timer = self.restart_overhead
            self.last_decision = ClusterType.NONE
            return ClusterType.NONE
        
        # Calculate time remaining until deadline
        time_remaining = self.deadline - self.time_elapsed
        
        # Calculate minimum time needed to finish (with on-demand)
        min_time_needed = self.remaining_work * self.gap_seconds
        
        # Calculate safety buffer
        safety_buffer = self.safety_margin * 3600  # Convert hours to seconds
        
        # If we're cutting it close, switch to on-demand
        if time_remaining - safety_buffer <= min_time_needed:
            self.last_decision = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        # If spot is available and we have enough time buffer, use it
        if has_spot:
            # Calculate expected time with spot (accounting for availability)
            expected_spot_time = min_time_needed / max(self.spot_availability, 0.01)
            
            # Add expected restart overheads
            expected_restarts = max(0, (expected_spot_time / 3600) * (1 - self.spot_availability))
            expected_time_with_restarts = expected_spot_time + expected_restarts * self.restart_overhead
            
            # If expected time with spot is safe, use it
            if time_remaining - safety_buffer >= expected_time_with_restarts:
                self.last_decision = ClusterType.SPOT
                return ClusterType.SPOT
        
        # If spot not available or not safe, use on-demand
        self.last_decision = ClusterType.ON_DEMAND
        return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
