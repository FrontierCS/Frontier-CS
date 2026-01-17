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

        self.num_regions = self.env.get_num_regions()
        
        # EWMA parameters for tracking region spot availability
        self.ewma_alpha = 0.2
        # Start optimistically, assuming all regions have good spot availability
        self.spot_availability_ewma = [1.0] * self.num_regions

        # Safety buffer for the critical path calculation. If the time required
        # to finish on on-demand is >= (remaining time - this buffer),
        # we force the use of on-demand to ensure we meet the deadline.
        self.ondemand_threshold = self.restart_overhead * 2.0

        # A region's estimated availability must be higher by this margin
        # to be considered for a switch. This prevents excessive switching.
        self.switch_margin = 0.05

        return self

    def _argmax(self, iterable):
        """Helper function to find the index of the maximum value in a list."""
        if not iterable:
            return -1
        return max(range(len(iterable)), key=iterable.__getitem__)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # 1. Update internal state based on new information
        current_region = self.env.get_current_region()

        has_spot_numeric = 1.0 if has_spot else 0.0
        old_ewma = self.spot_availability_ewma[current_region]
        self.spot_availability_ewma[current_region] = (
            self.ewma_alpha * has_spot_numeric + (1 - self.ewma_alpha) * old_ewma
        )

        # 2. Calculate remaining work and time
        work_done = sum(self.task_done_time)
        work_rem = self.task_duration - work_done

        if work_rem <= 0:
            return ClusterType.NONE

        time_rem = self.deadline - self.env.elapsed_seconds

        # 3. Critical Path Check (Highest Priority)
        # Calculate time needed to finish if we only use On-Demand from now on.
        time_needed_on_demand = work_rem + self.remaining_restart_overhead

        # If we are approaching a point where not using On-Demand risks missing
        # the deadline, we must use it.
        if time_needed_on_demand + self.ondemand_threshold >= time_rem:
            return ClusterType.ON_DEMAND

        # 4. Main Decision Logic (not on critical path)

        # 4a. Best Case: Spot is available.
        if has_spot:
            return ClusterType.SPOT

        # 4b. Spot is unavailable. Decide to switch, wait, or use On-Demand.
        
        # Region Switching Logic:
        best_region_idx = self._argmax(self.spot_availability_ewma)
        
        if best_region_idx != current_region:
            current_ewma = self.spot_availability_ewma[current_region]
            best_ewma = self.spot_availability_ewma[best_region_idx]

            # A switch incurs an overhead. Check if it's safe time-wise.
            time_needed_after_switch = work_rem + self.restart_overhead
            is_switch_safe = time_needed_after_switch < time_rem

            if best_ewma > current_ewma + self.switch_margin and is_switch_safe:
                self.env.switch_region(best_region_idx)
                # After switching, we don't know the spot status. Returning NONE
                # is a safe, zero-cost choice to observe the new region's state.
                return ClusterType.NONE

        # Stay-in-Region Logic (Wait vs. On-Demand):
        # Calculate available slack time if we were to finish on On-Demand.
        slack_time = time_rem - time_needed_on_demand

        # If we have more slack than one time step, we can afford to wait.
        if slack_time > self.env.gap_seconds:
            return ClusterType.NONE
        else:
            # Slack is tight; we cannot afford to lose a time step.
            # Use On-Demand to guarantee progress.
            return ClusterType.ON_DEMAND