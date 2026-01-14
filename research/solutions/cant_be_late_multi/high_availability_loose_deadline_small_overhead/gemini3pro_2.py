import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "robust_cost_optimizer"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.

        The spec file contains:
        - deadline: deadline in hours
        - duration: task duration in hours
        - overhead: restart overhead in hours
        - trace_files: list of trace file paths (one per region)
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
        """
        # 1. Calculate current progress and time budget
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If task is effectively complete, pause (the env will likely terminate)
        if work_remaining <= 1e-6:
            return ClusterType.NONE

        time_elapsed = self.env.elapsed_seconds
        time_until_deadline = self.deadline - time_elapsed

        # 2. Calculate Slack
        # Slack is the time buffer we have before we MUST run On-Demand to finish.
        # We calculate the time required to finish if we switched to On-Demand right now.
        
        # If we are already On-Demand, we just finish pending overhead + remaining work.
        # If we are NOT On-Demand, we incur a full restart overhead to switch.
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_to_finish = self.remaining_restart_overhead
        else:
            overhead_to_finish = self.restart_overhead

        time_needed_for_od = work_remaining + overhead_to_finish
        slack = time_until_deadline - time_needed_for_od

        # 3. Define Safety Buffer
        # We need a buffer to account for step quantization (gap_seconds) and safety.
        # 3 hours (or 3 steps) is a safe margin to absorb overheads and search costs
        # while keeping the high penalty at bay.
        gap = self.env.gap_seconds
        safe_buffer = max(3.0 * gap, 3.0 * 3600.0)

        # 4. Decision Logic
        
        # Panic Mode: If slack is tight, prioritize completion regardless of cost.
        if slack < safe_buffer:
            return ClusterType.ON_DEMAND

        # Cost Optimization Mode:
        # If Spot is available in current region, use it.
        if has_spot:
            return ClusterType.SPOT
        
        # Search Mode:
        # If Spot is unavailable here, and we have slack, explore other regions.
        # We switch region and return NONE to 'pause' and observe the new region's status in the next step.
        # This wastes time (eating into slack) but saves money if we find a Spot region.
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        next_region = (current_region + 1) % num_regions
        self.env.switch_region(next_region)
        
        return ClusterType.NONE