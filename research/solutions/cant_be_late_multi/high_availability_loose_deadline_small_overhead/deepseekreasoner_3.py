import json
from argparse import Namespace
from typing import List
import heapq
from collections import deque, defaultdict

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "smart_scheduler"

    def __init__(self, args):
        super().__init__(args)
        # Internal state
        self.region_count = None
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.step_size = None
        self.region_availability = None
        self.region_history = None
        self.consecutive_failures = None
        self.last_action = None
        self.safety_buffer = None
        self.critical_time = None
        self.patience_counter = None
        self.best_region = None
        
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
        
        # Initialize internal state
        self.spot_price = 0.9701  # $/hr
        self.ondemand_price = 3.06  # $/hr
        self.safety_buffer = 3600  # 1 hour buffer
        self.consecutive_failures = 0
        self.last_action = None
        self.patience_counter = 0
        self.best_region = 0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Initialize on first call
        if self.region_count is None:
            self.region_count = self.env.get_num_regions()
            self.step_size = self.env.gap_seconds
            self.region_availability = [deque(maxlen=100) for _ in range(self.region_count)]
            self.region_history = [[] for _ in range(self.region_count)]
            self.critical_time = self.deadline - self.safety_buffer - self.task_duration
        
        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        time_left = self.deadline - elapsed
        
        # Update region availability history
        self.region_availability[current_region].append(1 if has_spot else 0)
        
        # Critical check: must switch to on-demand if we're running out of time
        time_needed = remaining_work + (self.restart_overhead if last_cluster_type == ClusterType.NONE else 0)
        if time_left <= time_needed * 1.2:  # 20% safety margin
            return ClusterType.ON_DEMAND
        
        # If we have very little time left, use on-demand
        if time_left < remaining_work + self.restart_overhead * 3:
            return ClusterType.ON_DEMAND
        
        # Calculate spot availability metrics
        current_availability = sum(self.region_availability[current_region]) / max(len(self.region_availability[current_region]), 1)
        
        # If spot is available and we have good availability history, use spot
        if has_spot and current_availability > 0.7:
            self.consecutive_failures = 0
            self.last_action = ClusterType.SPOT
            return ClusterType.SPOT
        
        # If spot is not available in current region, consider switching
        if not has_spot:
            self.consecutive_failures += 1
            
            # If too many failures in current region, switch to another region
            if self.consecutive_failures > 3:
                # Find best region based on recent history
                best_region = current_region
                best_score = -1
                
                for region in range(self.region_count):
                    if region == current_region:
                        continue
                    
                    # Calculate availability score for this region
                    if self.region_availability[region]:
                        score = sum(self.region_availability[region]) / len(self.region_availability[region])
                        if score > best_score:
                            best_score = score
                            best_region = region
                
                self.env.switch_region(best_region)
                self.consecutive_failures = 0
                
                # After switching, use spot if available, otherwise pause
                return ClusterType.SPOT if has_spot else ClusterType.NONE
        
        # If we're here, spot is not available but we can't switch or don't want to
        # Use on-demand only if we're making good progress
        progress_ratio = work_done / max(elapsed, 1)
        if progress_ratio < 0.7 and time_left > remaining_work * 1.5:
            return ClusterType.ON_DEMAND
        
        # Otherwise, pause and wait for better conditions
        self.last_action = ClusterType.NONE
        return ClusterType.NONE