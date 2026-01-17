import json
from argparse import Namespace
from typing import List, Tuple
import heapq

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""
    
    NAME = "my_strategy"  # REQUIRED: unique identifier
    
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
        
        # Precompute trace data
        self.traces = []
        self.spot_availability = []
        self.num_regions = len(config["trace_files"])
        
        for trace_file in config["trace_files"]:
            with open(trace_file, 'r') as f:
                trace_data = json.load(f)
                self.traces.append(trace_data)
        
        # Convert hours to seconds
        self.deadline_seconds = float(config["deadline"]) * 3600
        self.task_duration_seconds = float(config["duration"]) * 3600
        self.restart_overhead_seconds = float(config["overhead"]) * 3600
        
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Get current state
        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        remaining_work = self.task_duration - sum(self.task_done_time)
        
        # If work is done, return NONE
        if remaining_work <= 0:
            return ClusterType.NONE
        
        # Calculate remaining time until deadline
        remaining_time = self.deadline - elapsed
        
        # Calculate effective time needed considering restart overhead
        effective_time_needed = remaining_work
        if self.remaining_restart_overhead > 0:
            effective_time_needed += min(self.remaining_restart_overhead, self.env.gap_seconds)
        
        # If we're critically short on time, use on-demand
        if remaining_time <= effective_time_needed + self.env.gap_seconds * 2:
            # Find a region where we can continue without interruption
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            else:
                # Switch to on-demand even if it incurs restart overhead
                return ClusterType.ON_DEMAND
        
        # Check if we can use spot in current region
        if has_spot:
            # Use spot if we have sufficient time buffer
            time_buffer = remaining_time - effective_time_needed
            if time_buffer >= self.restart_overhead * 2:  # Allow for at least one restart
                # If we're already on spot, continue
                if last_cluster_type == ClusterType.SPOT:
                    return ClusterType.SPOT
                else:
                    # Switch to spot if it's worth the potential restart
                    return ClusterType.SPOT
        
        # If spot not available in current region, check other regions
        if not has_spot or last_cluster_type == ClusterType.NONE:
            # Try to find a region with spot availability
            best_region = self._find_best_region(current_region, elapsed)
            if best_region != current_region:
                self.env.switch_region(best_region)
                # After switching, check if spot is available in new region
                if has_spot:
                    return ClusterType.SPOT
        
        # Default to on-demand if we have time but spot is risky
        if remaining_time > effective_time_needed + self.restart_overhead:
            return ClusterType.ON_DEMAND
        
        # Otherwise, wait
        return ClusterType.NONE
    
    def _find_best_region(self, current_region: int, current_time: float) -> int:
        """
        Find the best region to switch to based on estimated spot availability.
        """
        best_region = current_region
        best_score = -float('inf')
        
        # Calculate time steps
        time_step = self.env.gap_seconds
        current_step = int(current_time / time_step)
        lookahead_steps = min(10, int((self.deadline - current_time) / time_step))
        
        for region in range(self.env.get_num_regions()):
            if region == current_region:
                continue
            
            # Simple heuristic: count available spot steps in lookahead window
            available_count = 0
            for step_offset in range(lookahead_steps):
                step = current_step + step_offset
                if step < len(self.traces[region]):
                    if self.traces[region][step]:  # Spot available
                        available_count += 1
            
            # Prefer regions with high spot availability
            score = available_count / max(1, lookahead_steps)
            
            # Slight penalty for switching away from current region
            if region != current_region:
                score -= 0.1
            
            if score > best_score:
                best_score = score
                best_region = region
        
        return best_region