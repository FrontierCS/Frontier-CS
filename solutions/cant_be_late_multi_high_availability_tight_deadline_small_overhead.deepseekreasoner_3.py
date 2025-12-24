import json
from argparse import Namespace
from typing import List
import heapq
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""
    
    NAME = "efficient_multi_region"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.
        """
        with open(spec_path) as f:
            config = json.load(f)
        
        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)
        
        # Read and preprocess traces
        self.traces = []
        for trace_file in config["trace_files"]:
            with open(trace_file) as f:
                # Trace format: one availability per line (0/1)
                trace_data = [int(line.strip()) for line in f]
                self.traces.append(trace_data)
        
        self.num_regions = len(self.traces)
        self.step_size = 3600  # Assuming 1-hour steps based on problem description
        self.total_steps = int(36 * 3600 / self.step_size)  # 36 hours in steps
        
        # Precompute region spot availability patterns
        self.region_availability = []
        for region_idx in range(self.num_regions):
            # Convert to list of available steps
            available_steps = [i for i, avail in enumerate(self.traces[region_idx]) if avail == 1]
            self.region_availability.append(available_steps)
        
        # Cost parameters
        self.spot_cost = 0.9701
        self.ondemand_cost = 3.06
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        current_region = self.env.get_current_region()
        current_time = self.env.elapsed_seconds
        
        # Calculate progress
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - current_time
        
        # Calculate current step index
        current_step = int(current_time / self.step_size)
        
        # If we're in restart overhead, continue with current type if possible
        if self.remaining_restart_overhead > 0:
            if last_cluster_type == ClusterType.SPOT and has_spot:
                return ClusterType.SPOT
            elif last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            # If we can't continue with current type, switch to available option
        
        # Emergency mode: if we're running out of time, use on-demand
        time_needed_with_overhead = work_remaining + self.restart_overhead
        if time_remaining <= time_needed_with_overhead + self.step_size:
            # Check if we can stay in current region with spot
            if has_spot and last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            # Otherwise use on-demand
            return ClusterType.ON_DEMAND
        
        # Find best region for spot availability in near future
        best_region = current_region
        best_score = -1
        
        # Look ahead 6 hours for spot availability
        lookahead_steps = min(6, int(time_remaining / self.step_size))
        
        for region in range(self.num_regions):
            # Check spot availability in this region for next few steps
            available_count = 0
            for offset in range(lookahead_steps):
                step = current_step + offset
                if step < len(self.traces[region]) and self.traces[region][step] == 1:
                    available_count += 1
            
            # Calculate score: availability minus switching penalty
            score = available_count
            if region != current_region:
                score -= 0.5  # Small penalty for switching
            
            if score > best_score:
                best_score = score
                best_region = region
        
        # Switch to best region if different
        if best_region != current_region:
            self.env.switch_region(best_region)
            # Update has_spot for new region
            if current_step < len(self.traces[best_region]):
                has_spot = (self.traces[best_region][current_step] == 1)
            else:
                has_spot = False
        
        # Decision logic
        if has_spot:
            # Use spot if available and we have time buffer
            time_buffer_needed = 2 * self.step_size + self.restart_overhead
            if time_remaining > work_remaining + time_buffer_needed:
                return ClusterType.SPOT
            # If buffer is tight but we were already on spot, continue
            elif last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            # Otherwise use on-demand for reliability
            else:
                return ClusterType.ON_DEMAND
        else:
            # No spot available
            if work_remaining <= time_remaining - self.step_size:
                # We have some slack, wait for spot
                return ClusterType.NONE
            else:
                # Need to make progress, use on-demand
                return ClusterType.ON_DEMAND
