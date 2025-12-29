import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"

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
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        Prioritizes finishing the task before deadline, then minimizes cost.
        """
        # Calculate remaining work and time
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        # Effective work needed includes the task duration plus any currently pending overhead
        effective_work_needed = work_remaining + self.remaining_restart_overhead
        
        # Slack: How much "extra" time we have beyond the minimum required to finish
        slack = time_remaining - effective_work_needed
        
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Safety Threshold:
        # We need to guarantee completion. If we fall below this buffer, we must force On-Demand.
        # Buffer composition:
        # 1. restart_overhead: If we switch to OD/Spot now, we might incur new overhead.
        # 2. 2 * gap: Buffer for the current decision step and discrete time quantization.
        safety_threshold = 2.0 * gap + 1.1 * overhead
        
        # 1. Safety Check: If slack is tight, force On-Demand to guarantee completion
        if slack < safety_threshold:
            return ClusterType.ON_DEMAND

        # 2. Cost Optimization: Try to use Spot if available
        if has_spot:
            # Spot is available in the current region
            return ClusterType.SPOT
        else:
            # Spot is unavailable in current region, but we have slack.
            # Strategy: Probe other regions.
            # Action: Switch region and return NONE (Pause).
            # This costs 'gap' time (reducing slack) but $0 money.
            # In the next step, we will check availability in the new region.
            
            num_regions = self.env.get_num_regions()
            current_region = self.env.get_current_region()
            next_region = (current_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            
            return ClusterType.NONE