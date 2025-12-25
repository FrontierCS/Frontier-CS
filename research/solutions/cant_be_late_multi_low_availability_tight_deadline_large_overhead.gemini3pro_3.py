import json
from argparse import Namespace
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType

class Solution(MultiRegionStrategy):
    """Adaptive multi-region scheduling strategy."""

    NAME = "adaptive_switcher"

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
        self.overhead_seconds = float(config["overhead"]) * 3600.0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work
        done = sum(self.task_done_time)
        needed = self.task_duration - done
        
        # Task complete check
        if needed <= 1e-6:
            return ClusterType.NONE

        time_now = self.env.elapsed_seconds
        time_left = self.deadline - time_now
        
        # Calculate minimum time to finish if we switch to/stay on OD immediately
        if last_cluster_type == ClusterType.ON_DEMAND:
            pending = self.remaining_restart_overhead
        else:
            # If switching to OD, we incur restart overhead
            pending = max(self.remaining_restart_overhead, self.overhead_seconds)
            
        time_needed_od = needed + pending
        slack = time_left - time_needed_od
        
        # Strategy Thresholds (in seconds)
        # PANIC_BUFFER: If slack falls below this, force OD to ensure deadline
        PANIC_BUFFER = 3600.0  # 1 hour
        # SEARCH_BUFFER: If slack is above this, we can afford to idle (NONE) while switching regions to find Spot
        SEARCH_BUFFER = 4.0 * 3600.0 # 4 hours
        
        # 1. Panic Mode: Ensure deadline met
        if slack < PANIC_BUFFER:
            return ClusterType.ON_DEMAND
            
        # 2. Prefer Spot if available
        if has_spot:
            return ClusterType.SPOT
            
        # 3. No Spot available in current region
        # Switch to next region to check availability in next step
        curr = self.env.get_current_region()
        total_regions = self.env.get_num_regions()
        self.env.switch_region((curr + 1) % total_regions)
        
        # Decision after switch:
        # If we have plenty of slack, return NONE to wait and save money.
        # If slack is moderate (but not panic), return OD to make progress while moving.
        if slack > SEARCH_BUFFER:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND
