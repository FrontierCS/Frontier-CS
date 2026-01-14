import json
from argparse import Namespace
from collections import deque

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that aims to minimize cost while guaranteeing
    task completion before the deadline.

    The strategy operates in two main modes:
    1.  **Normal Mode**: Prioritizes using cheap Spot instances. If Spot is
        unavailable in the current region, it uses historical availability data
        to decide whether to switch to a more promising region or fall back to
        a more expensive On-Demand instance.
    2.  **Panic Mode**: If the time remaining is critically low, the strategy
        switches to using On-Demand instances exclusively to ensure the task
        finishes on time, as this is the highest priority.

    Region switching is treated as a "probe": if the current region has a poor
    Spot availability track record and another region looks better, the strategy
    switches and waits one time step (ClusterType.NONE) to observe the new
    region's state. This is only done if there is sufficient time slack to
    absorb the cost of the probe (one time step + restart overhead).
    """

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

        # Custom initialization for strategy state
        self._initialized = False
        self._num_regions = 0
        self._spot_history = {}
        self._consecutive_no_spot = {}
        
        # --- Strategy Hyperparameters ---
        # Look at last 12 hours/steps for availability estimates
        self._history_window_size = 12
        # Consider switching after this many consecutive hours of no spot
        self._switch_consecutive_threshold = 2
        # Target region must have at least this estimated availability to be worth switching
        self._switch_availability_threshold = 0.80
        # Prior belief about spot availability for unexplored regions
        self._unexplored_region_prior = 0.95

        return self

    def _initialize_state(self):
        """Lazy initialization on the first call to _step."""
        if not self._initialized:
            self._num_regions = self.env.get_num_regions()
            self._spot_history = {
                i: deque(maxlen=self._history_window_size) for i in range(self._num_regions)
            }
            self._consecutive_no_spot = {i: 0 for i in range(self._num_regions)}
            self._initialized = True

    def _update_history(self, current_region: int, has_spot: bool):
        """Update historical data for the current region."""
        self._spot_history[current_region].append(1 if has_spot else 0)

        if not has_spot:
            self._consecutive_no_spot[current_region] += 1
        else:
            self._consecutive_no_spot[current_region] = 0

    def _get_region_availabilities(self) -> dict[int, float]:
        """Calculate estimated spot availability for all regions based on history."""
        availabilities = {}
        for r in range(self._num_regions):
            hist = self._spot_history[r]
            if not hist:
                # Use an optimistic prior for unexplored regions
                availabilities[r] = self._unexplored_region_prior
            else:
                availabilities[r] = sum(hist) / len(hist)
        return availabilities

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide the next action based on the current state of the environment.
        """
        self._initialize_state()

        current_region = self.env.get_current_region()
        self._update_history(current_region, has_spot)

        work_done = sum(self.task_done_time)
        if work_done >= self.task_duration:
            return ClusterType.NONE

        work_remaining = self.task_duration - work_done
        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # --- Panic Mode Check ---
        # Enter panic mode if time left is less than work left plus a buffer
        # for one potential failure (e.g., a preemption). A single failure costs
        # one time step of progress and incurs a restart overhead.
        panic_buffer = self.env.gap_seconds + self.restart_overhead
        if time_to_deadline <= work_remaining + panic_buffer:
            return ClusterType.ON_DEMAND

        # --- Normal Operation ---
        if has_spot:
            return ClusterType.SPOT

        # --- No Spot: Decide between On-Demand or Switching Region ---
        availabilities = self._get_region_availabilities()
        
        best_other_region = -1
        max_availability = -1.0
        # Find the most promising region to switch to
        for r in range(self._num_regions):
            if r == current_region:
                continue
            if availabilities[r] > max_availability:
                max_availability = availabilities[r]
                best_other_region = r

        # Condition to attempt a switch:
        # 1. Current region has been without spot for a while.
        # 2. There is a significantly more promising region.
        should_probe = (
            self._consecutive_no_spot[current_region] >= self._switch_consecutive_threshold and
            best_other_region != -1 and
            max_availability >= self._switch_availability_threshold
        )

        if should_probe:
            # A "probe" move (switch + NONE) costs time. Check if we can afford it.
            # The time cost is one time step (for NONE) plus the restart overhead.
            probe_time_cost = self.env.gap_seconds + self.restart_overhead
            
            # If making this move would put us into panic mode, it's too risky.
            if (time_to_deadline - probe_time_cost) <= (work_remaining + panic_buffer):
                should_probe = False

        if should_probe:
            # Execute the probe: switch to the best candidate region and wait.
            self.env.switch_region(best_other_region)
            # Reset the counter for the region we are leaving.
            self._consecutive_no_spot[current_region] = 0
            return ClusterType.NONE
        else:
            # It's not worth switching or it's too risky. Fall back to On-Demand.
            return ClusterType.ON_DEMAND