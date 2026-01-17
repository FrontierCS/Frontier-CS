import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cost_optimized_deadline_aware_strategy"

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
        Prioritize Spot instances to save cost, but switch to On-Demand
        if the deadline is approaching to avoid the heavy penalty.
        """
        # 1. Calculate current progress and time
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        total_duration = self.task_duration
        remaining_work = total_duration - done

        # Check if work is completed (should be handled by env, but explicit check is safe)
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        deadline = self.deadline
        time_left = deadline - elapsed
        
        # 2. Parameters
        # Use provided overhead. If we are currently restarting, the env handles the accounting,
        # but for our calculation, we assume the worst-case scenario where we might need a full restart overhead.
        overhead = self.restart_overhead
        gap = self.env.gap_seconds

        # 3. Safety / Panic Logic
        # We must ensure we have enough time to finish the job using reliable On-Demand instances.
        # Time required on OD = remaining_work + overhead (time to boot OD instance).
        # We add a buffer because:
        # a) We make decisions in discrete time steps (gap_seconds). If we choose Spot or None now,
        #    we commit to that for 'gap' seconds.
        # b) If we choose Spot and it fails/preempts, or we choose None to switch regions, 
        #    we effectively lose 'gap' time from the deadline.
        #
        # Therefore, we must switch to OD if:
        # time_left < (Time needed for OD) + (Time we might lose in this step)
        
        # Buffer includes the current step gap (plus a small margin) and the overhead.
        # We use 1.5 * gap to be safe against boundary conditions.
        safety_buffer = gap * 1.5 + overhead
        required_time_on_od = remaining_work + overhead
        
        if time_left < (required_time_on_od + safety_buffer):
            # We are close to the deadline. Force On-Demand to guarantee completion.
            return ClusterType.ON_DEMAND

        # 4. Cost Optimization Logic
        # If we are safe (have plenty of slack), we prioritize Spot instances.
        
        if has_spot:
            # Spot is available in the current region. Use it.
            return ClusterType.SPOT
        else:
            # Spot is not available in the current region.
            # Because we have slack (checked above), we can afford to search for Spot in other regions.
            # We switch to the next region and return NONE for this step.
            # Returning NONE means we pause for 'gap_seconds' while switching/searching.
            # In the next step, has_spot will reflect the availability in the new region.
            
            num_regions = self.env.get_num_regions()
            current_region = self.env.get_current_region()
            next_region = (current_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            
            return ClusterType.NONE