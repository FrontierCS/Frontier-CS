import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "CostMinimizerStrategy"

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
        
        Strategy:
        1. Calculate 'slack' (time remaining minus work remaining and overhead).
        2. Panic Mode: If slack is below a safety buffer, force On-Demand to guarantee completion.
           On-Demand is expensive but reliable.
        3. Spot Mode: If not in panic mode and Spot is available in current region, use Spot.
           Spot is cheap but unreliable.
        4. Search Mode: If Spot is unavailable in current region, switch to next region and wait.
           This cycles through regions to find one with Spot availability.
        """
        # Retrieve environment state
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        work_remaining = self.task_duration - done
        
        # If task is logically complete, stop (return NONE)
        if work_remaining <= 0:
            return ClusterType.NONE

        time_remaining = self.deadline - elapsed
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Calculate Safety Buffer
        # We need a buffer to handle:
        # - The overhead of switching to On-Demand if Spot fails.
        # - Loss of the current time step (gap) if a failure/switch occurs.
        # - A fixed safety margin (e.g., 1 hour) to account for simulation granularity and edge cases.
        # Buffer = 2 * step_size + 2 * overhead + 1 hour (3600s)
        safe_buffer = max(2.0 * gap, 3600.0) + 2.0 * overhead
        
        # Calculate Slack
        # Time we have left minus time we strictly need (Work + Overhead to start OD)
        slack = time_remaining - (work_remaining + overhead)
        
        # 1. Panic Mode: If slack is dangerously low, switch to On-Demand.
        # This ensures we meet the deadline (avoiding the -100,000 penalty) even if it costs more.
        if slack < safe_buffer:
            return ClusterType.ON_DEMAND

        # 2. Spot Mode: If we have enough slack, prefer Spot to save money.
        if has_spot:
            return ClusterType.SPOT

        # 3. Search Mode: Spot is not available in the current region.
        # We cannot check other regions without switching.
        # Switch to the next region in a round-robin fashion.
        next_region_idx = (self.env.get_current_region() + 1) % self.env.get_num_regions()
        self.env.switch_region(next_region_idx)
        
        # After switching, we don't know if the new region has Spot until the next step.
        # We return NONE to "pause" and avoid paying for On-Demand while searching.
        return ClusterType.NONE