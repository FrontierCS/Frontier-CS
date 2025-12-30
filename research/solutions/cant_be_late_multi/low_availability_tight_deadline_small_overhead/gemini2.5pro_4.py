import json
from argparse import Namespace
from collections import deque

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

        self.num_regions = self.env.get_num_regions()
        
        # Hyperparameters
        self.history_window = 36
        self.uptime_threshold = 0.6
        self.panic_buffer_factor = 1.25
        self.min_time_between_switches = self.restart_overhead * 3
        
        # State tracking
        self.region_history = [
            deque(maxlen=self.history_window) for _ in range(self.num_regions)
        ]
        
        # Seed history to encourage exploration
        for i in range(self.num_regions):
            self.region_history[i].append(1)

        self.last_switch_time = -self.min_time_between_switches * 2

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
        current_region = self.env.get_current_region()
        time_elapsed = self.env.elapsed_seconds

        # Update history for the current region
        self.region_history[current_region].append(1 if has_spot else 0)

        # Calculate remaining work
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If task is done, do nothing to save cost
        if work_remaining <= 0:
            return ClusterType.NONE

        # Calculate time left until deadline
        time_remaining_until_deadline = self.deadline - time_elapsed

        # Failsafe for being at/past the deadline
        if time_remaining_until_deadline <= 1e-6:
            return ClusterType.ON_DEMAND

        # Determine if we are in a "critical" or "panic" state
        # This happens when remaining time is close to the minimum time needed to finish
        # assuming reliable On-Demand usage, plus a safety buffer for one more restart event.
        time_needed_for_safe_completion = work_remaining + self.panic_buffer_factor * self.restart_overhead
        is_critical = time_remaining_until_deadline <= time_needed_for_safe_completion

        if is_critical:
            # Panic Mode: Guarantee progress with On-Demand
            return ClusterType.ON_DEMAND

        # Normal Mode: We have slack, prioritize cost savings
        if has_spot:
            # Use cheap Spot when available
            return ClusterType.SPOT
        else:
            # Spot is unavailable. Decide between On-Demand or switching region.
            
            # Avoid switching too frequently ("thrashing")
            time_since_last_switch = time_elapsed - self.last_switch_time
            if time_since_last_switch < self.min_time_between_switches:
                return ClusterType.ON_DEMAND

            # Evaluate other regions based on historical spot uptime
            uptimes = []
            for i in range(self.num_regions):
                hist = self.region_history[i]
                if not hist:
                    uptimes.append(1.0)  # Assume 100% uptime if no history
                else:
                    uptimes.append(sum(hist) / len(hist))

            # Find the best alternative region to switch to
            best_other_region_idx = -1
            max_uptime = -1.0
            
            # Iterate through potential regions in a fixed order to break ties
            candidate_indices = (
                list(range(current_region + 1, self.num_regions)) +
                list(range(0, current_region))
            )

            for i in candidate_indices:
                if uptimes[i] > max_uptime:
                    max_uptime = uptimes[i]
                    best_other_region_idx = i

            # If a promising region is found, switch to it
            if best_other_region_idx != -1 and max_uptime > self.uptime_threshold:
                self.env.switch_region(best_other_region_idx)
                self.last_switch_time = time_elapsed
                # A switch incurs overhead, so return NONE to save cost this step
                return ClusterType.NONE
            else:
                # No other region looks good enough, so use On-Demand to make progress
                return ClusterType.ON_DEMAND