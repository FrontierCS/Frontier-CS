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

        # Load spot availability traces from files
        self.spot_availability = []
        for trace_file in config["trace_files"]:
            with open(trace_file) as f:
                trace = [line.strip() == '1' for line in f]
                self.spot_availability.append(trace)

        if not self.spot_availability:
            self.num_regions = 0
            self.num_steps = 0
            return self

        self.num_regions = len(self.spot_availability)
        self.num_steps = len(self.spot_availability[0])

        # Precompute the next available spot timestep for efficient lookups
        self.next_spot_step = [[-1] * self.num_steps for _ in range(self.num_regions)]
        for r in range(self.num_regions):
            next_s = -1
            # Iterate backwards to fill in the next available step
            for t in range(self.num_steps - 1, -1, -1):
                if self.spot_availability[r][t]:
                    next_s = t
                self.next_spot_step[r][t] = next_s

        # A buffer for panic mode, as a multiple of restart_overhead.
        self.PANIC_BUFFER_FACTOR = 3.0

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
        if self.num_regions == 0:
            return ClusterType.ON_DEMAND
        
        current_step = int(self.env.elapsed_seconds // self.env.gap_seconds)
        if current_step >= self.num_steps:
            return ClusterType.ON_DEMAND

        progress = sum(self.task_done_time)
        remaining_work = self.task_duration - progress

        if remaining_work <= 1e-9:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        
        # Panic mode: if time is tight, switch to reliable On-Demand
        panic_threshold = remaining_work + self.restart_overhead * self.PANIC_BUFFER_FACTOR
        if time_to_deadline <= panic_threshold:
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()

        # Normal mode: prefer Spot. First, check for any available Spot *now*.
        target_region = -1
        if has_spot:
            target_region = current_region
        else:
            for r in range(self.num_regions):
                if self.spot_availability[r][current_step]:
                    target_region = r
                    break
        
        # If a Spot instance is available, switch to it.
        if target_region != -1:
            if target_region != current_region:
                self.env.switch_region(target_region)
            return ClusterType.SPOT

        # No Spot available now. Decide whether to wait or use On-Demand.
        # Find the soonest future Spot availability.
        min_next_spot_step = -1
        for r in range(self.num_regions):
            next_s = self.next_spot_step[r][current_step]
            if next_s != -1:
                if min_next_spot_step == -1 or next_s < min_next_spot_step:
                    min_next_spot_step = next_s
        
        # If no Spot will ever be available again, must use On-Demand.
        if min_next_spot_step == -1:
            return ClusterType.ON_DEMAND

        # Calculate if we can afford to wait for the next Spot window.
        wait_steps = min_next_spot_step - current_step
        time_to_wait = wait_steps * self.env.gap_seconds
        
        # Time projection if we wait: wait time + one restart + remaining work
        total_time_if_wait = time_to_wait + self.restart_overhead + remaining_work
        
        if total_time_if_wait < time_to_deadline:
            # It's safe and cheaper to wait.
            return ClusterType.NONE
        else:
            # Cannot afford to wait, must use On-Demand to make progress.
            return ClusterType.ON_DEMAND