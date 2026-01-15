import json
import random
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)
        
        self.ban_until = {}
        self.cooldown = 7200.0  # 2 hours cooldown for bad regions
        self.safety_buffer = 18000.0  # 5 hours safety buffer
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        current_time = self.env.elapsed_seconds
        
        # Mark current region as bad if no spot available
        if not has_spot:
            self.ban_until[current_region] = current_time + self.cooldown
            
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - current_time
        
        # Calculate effective overhead if we were to switch to OD or restart
        if last_cluster_type == ClusterType.ON_DEMAND:
            pending_overhead = self.remaining_restart_overhead
        else:
            pending_overhead = self.restart_overhead
            
        # Calculate Slack
        slack = time_remaining - (work_remaining + pending_overhead)
        
        # Panic Mode: If slack is too low, use On-Demand to guarantee completion
        if slack < self.safety_buffer:
            return ClusterType.ON_DEMAND
            
        # Spot Mode: If available, use Spot
        if has_spot:
            return ClusterType.SPOT
            
        # Search Mode: Switch region if current doesn't have Spot
        num_regions = self.env.get_num_regions()
        candidates = []
        for r in range(num_regions):
            if r == current_region:
                continue
            if self.ban_until.get(r, 0) <= current_time:
                candidates.append(r)
                
        target = -1
        if candidates:
            target = random.choice(candidates)
        else:
            # If all valid candidates are banned, try the one expiring soonest
            others = [r for r in range(num_regions) if r != current_region]
            if others:
                target = min(others, key=lambda x: self.ban_until.get(x, 0))
                
        if target != -1:
            self.env.switch_region(target)
            # Return NONE to handle overhead and allow next step to check availability
            return ClusterType.NONE
            
        # Fallback if no other regions exist
        return ClusterType.NONE