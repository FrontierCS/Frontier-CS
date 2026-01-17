import json
from argparse import Namespace
import math

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

        # Custom initialization
        self.num_regions = self.env.get_num_regions()
        
        # Hyperparameters
        # How much extra slack (in multiples of gap_seconds) to have before choosing to wait (NONE).
        self.WAIT_SLACK_FACTOR = 2.0
        # Switch away from a region if it has this many consecutive spot outages.
        self.SWITCH_OUTAGE_THRESHOLD = 1

        # State tracking across steps
        # Stores the number of consecutive timesteps spot has been unavailable in each region.
        self.consecutive_outages = [0] * self.num_regions
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Available attributes:
        - self.env.get_current_region(): Get current region index
        - self.env.get_num_regions(): Get total number of regions
        - self.env.switch_region(idx): Switch to region by index
        - self.env.elapsed_seconds: Current time elapsed
        - self.task_duration: Total task duration needed (seconds)
        - self.deadline: Deadline time (seconds)
        - self.restart_overhead: Restart overhead (seconds)
        - self.task_done_time: List of completed work segments
        - self.remaining_restart_overhead: Current pending overhead

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # 1. Update state and calculate key metrics
        current_region = self.env.get_current_region()
        
        if has_spot:
            self.consecutive_outages[current_region] = 0
        else:
            self.consecutive_outages[current_region] += 1
            
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If task is done, do nothing to save cost.
        if work_remaining <= 0:
            return ClusterType.NONE

        time_now = self.env.elapsed_seconds
        time_to_deadline = self.deadline - time_now

        # Calculate the time required to finish if we switch to on-demand now.
        # This is our safety baseline. We assume a restart overhead for a safe estimate.
        time_needed_for_od = work_remaining + self.restart_overhead
        steps_needed_for_od = math.ceil(time_needed_for_od / self.env.gap_seconds)
        on_demand_guarantee_time = steps_needed_for_od * self.env.gap_seconds

        # 2. Decision Logic

        # PANIC MODE: If remaining time is less than or equal to the time needed for the
        # safest option (on-demand), we must use on-demand. Don't switch regions
        # as that would incur more overhead.
        if time_to_deadline <= on_demand_guarantee_time:
            return ClusterType.ON_DEMAND

        # NORMAL MODE: We have some slack time.
        if has_spot:
            # Spot is available and is the cheapest option.
            return ClusterType.SPOT
        else:
            # Spot is not available in the current region.
            
            # 2a. Decide whether to switch to a new region for the *next* step.
            # We look for a region with a better spot availability history (fewer outages).
            min_outages = min(self.consecutive_outages)
            
            # If the current region is not among the best (ones with min_outages),
            # it's a candidate for switching away from.
            if self.consecutive_outages[current_region] > min_outages:
                # Switch if the number of outages has passed our threshold.
                if self.consecutive_outages[current_region] >= self.SWITCH_OUTAGE_THRESHOLD:
                    # Find the first region with the minimum number of outages and switch to it.
                    best_region_idx = self.consecutive_outages.index(min_outages)
                    self.env.switch_region(best_region_idx)

            # 2b. Decide what to do in the *current* step (ON_DEMAND or NONE).
            # Since has_spot is False, we can't use SPOT.
            # The choice depends on how much slack we have.
            wait_threshold_time = on_demand_guarantee_time + self.WAIT_SLACK_FACTOR * self.env.gap_seconds
            
            if time_to_deadline <= wait_threshold_time:
                # Slack is getting tight. We should make progress using on-demand.
                return ClusterType.ON_DEMAND
            else:
                # We have plenty of slack. We can afford to wait (NONE) for one step,
                # hoping spot becomes available soon, either here or in the new region.
                return ClusterType.NONE