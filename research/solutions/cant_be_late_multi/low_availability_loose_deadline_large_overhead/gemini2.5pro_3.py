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

        # Custom state for the strategy
        self.is_initialized = False
        self.num_regions = 0
        self.spot_history = []
        self.total_steps_seen = 0

        # --- Tunable Hyperparameters ---
        # UCB exploration constant
        self.ucb_c = math.sqrt(2.0)
        
        # Safety margin for switching to On-Demand, as a multiple of restart_overhead.
        self.safety_margin_factor = 1.0
        self.safety_margin_seconds = self.safety_margin_factor * self.restart_overhead
        
        return self

    def _initialize_state(self):
        """
        One-time initialization on the first call to _step,
        as the environment (`self.env`) is only available then.
        """
        self.num_regions = self.env.get_num_regions()
        
        # Initialize with a Beta(1,1) prior to encourage exploration
        # and avoid division by zero (i.e., assume 1 success, 1 failure).
        self.spot_history = [{'seen': 2, 'available': 1} for _ in range(self.num_regions)]
        self.total_steps_seen = self.num_regions * 2
        
        self.is_initialized = True

    def _get_best_region_ucb(self) -> int:
        """
        Finds the best region to be in using the UCB1 algorithm.
        """
        if self.total_steps_seen == 0:
            return self.env.get_current_region()

        ucb_scores = []
        log_total_steps = math.log(self.total_steps_seen)

        for i in range(self.num_regions):
            history = self.spot_history[i]
            
            mean_availability = history['available'] / history['seen']
            exploration_term = self.ucb_c * math.sqrt(log_total_steps / history['seen'])
            ucb_scores.append(mean_availability + exploration_term)
        
        return max(range(self.num_regions), key=lambda i: ucb_scores[i])

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
        # --- 1. Initialization ---
        if not self.is_initialized:
            self._initialize_state()

        # --- 2. State Update ---
        current_region = self.env.get_current_region()
        self.spot_history[current_region]['seen'] += 1
        self.total_steps_seen += 1
        if has_spot:
            self.spot_history[current_region]['available'] += 1
        
        # --- 3. Check for Task Completion ---
        work_done = sum(self.task_done_time)
        if work_done >= self.task_duration:
            return ClusterType.NONE

        # --- 4. "Panic Mode" Check ---
        work_rem = self.task_duration - work_done
        time_rem = self.deadline - self.env.elapsed_seconds
        
        # Time required if we switch to On-Demand now, conservatively
        # assuming a restart overhead will be incurred.
        time_needed_for_od = work_rem + self.restart_overhead

        if time_rem <= time_needed_for_od + self.safety_margin_seconds:
            return ClusterType.ON_DEMAND

        # --- 5. "Opportunistic Mode" ---
        if has_spot:
            # Spot is available, use it.
            return ClusterType.SPOT
        else:
            # Spot is not available. Use UCB to find the most promising region.
            best_region_to_be_in = self._get_best_region_ucb()

            if best_region_to_be_in != current_region:
                self.env.switch_region(best_region_to_be_in)

            # Since 'has_spot' was False, we cannot return SPOT.
            # Wait by returning NONE to save cost, leveraging the time slack.
            return ClusterType.NONE