import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cost_optimized_strategy"  # REQUIRED: unique identifier

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
        # Calculate remaining work
        done_work = sum(self.task_done_time)
        work_needed = self.task_duration - done_work

        # If task is basically done, stop
        if work_needed <= 1e-6:
            return ClusterType.NONE

        # Calculate time constraints
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        gap = self.env.gap_seconds
        overhead = self.restart_overhead

        # Define Panic Threshold
        # If remaining time is close to required time, force On-Demand.
        # We need: work_needed + potential overhead.
        # We add a buffer of 2.0 * gap to ensure we switch safely before it's too late,
        # accounting for the discrete time steps.
        panic_threshold = work_needed + overhead + (2.0 * gap)

        if time_left < panic_threshold:
            # Risk of missing deadline: use On-Demand immediately
            return ClusterType.ON_DEMAND

        if has_spot:
            # Safe to use Spot: cheapest option
            return ClusterType.SPOT

        # Spot unavailable in current region, but we have time slack.
        # Strategy: Switch to the next region and wait one step.
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        next_region = (current_region + 1) % num_regions
        
        self.env.switch_region(next_region)

        # We return NONE to avoid paying for On-Demand while searching.
        # This consumes 'gap' time but 0 money.
        # In the next step, we will check has_spot for the new region.
        return ClusterType.NONE