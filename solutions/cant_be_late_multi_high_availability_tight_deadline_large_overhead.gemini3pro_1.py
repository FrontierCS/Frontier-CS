import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

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

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Gather current state information
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        remaining_work = self.task_duration - done
        time_remaining = self.deadline - elapsed
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Panic Threshold Calculation
        # We need enough time to finish remaining work plus some buffer for overheads.
        # If time is below this threshold, we stop exploring and stick to safe resources.
        # Buffer = 3 * overhead allows for a few unexpected restarts/transitions.
        safe_buffer = 3.0 * overhead
        is_panic = time_remaining < (remaining_work + safe_buffer)

        if is_panic:
            # Panic Mode: Prioritize finishing over cost.
            # If Spot is available, use it (cheapest way to finish).
            if has_spot:
                return ClusterType.SPOT
            else:
                # Force On-Demand. Do NOT switch regions to avoid further overhead penalties.
                return ClusterType.ON_DEMAND

        # Normal Mode: We have slack time.
        # Prioritize Spot instances.
        if has_spot:
            return ClusterType.SPOT

        # If Spot is unavailable in current region, search elsewhere.
        # Switch to the next region (Round Robin).
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        next_region = (current_region + 1) % num_regions
        self.env.switch_region(next_region)

        # After switching, we need to decide the action for the *next* step.
        # We don't know if the new region has Spot yet.
        # If the time step (gap) is small (e.g., < 5 mins), return NONE.
        # This acts as a cheap "probe" to check availability without paying OD costs.
        # If the time step is large (e.g., 1 hour), return ON_DEMAND.
        # This ensures we make progress (paying OD cost + overhead) rather than wasting a huge chunk of time.
        if gap < 300.0:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND
