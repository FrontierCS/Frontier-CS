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

        # Custom initialization for the strategy's state and hyperparameters
        self.initialized = False
        self.num_regions = -1
        self.consecutive_failures = []
        
        # Hyperparameters
        self.patience = 3
        self.safety_preemptions = 2
        
        # State for efficient work tracking
        self.work_done = 0.0
        self.last_task_done_len = 0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        if not self.initialized:
            self.num_regions = self.env.get_num_regions()
            self.consecutive_failures = [0] * self.num_regions
            self.safety_buffer = self.safety_preemptions * (self.env.gap_seconds + self.restart_overhead)
            self.initialized = True

        current_region = self.env.get_current_region()
        if has_spot:
            self.consecutive_failures[current_region] = 0
        else:
            self.consecutive_failures[current_region] += 1
        
        # Efficiently update the total work done
        if len(self.task_done_time) > self.last_task_done_len:
            # sum() is only called on the new segments, keeping this step fast.
            new_segments = self.task_done_time[self.last_task_done_len:]
            self.work_done += sum(new_segments)
            self.last_task_done_len = len(self.task_done_time)
            
        remaining_work = self.task_duration - self.work_done

        if remaining_work <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        
        time_needed_on_demand = remaining_work + self.remaining_restart_overhead

        # Urgency check: If slack is below the safety buffer, force On-Demand.
        if time_needed_on_demand >= time_left - self.safety_buffer:
            return ClusterType.ON_DEMAND

        # Standard operation: Prioritize cost-saving if not in danger.
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot unavailable: decide whether to use On-Demand or switch regions.
            if self.num_regions > 1 and self.consecutive_failures[current_region] >= self.patience:
                # Switch region if current one is persistently unavailable.
                next_region = (current_region + 1) % self.num_regions
                self.env.switch_region(next_region)
                # Use On-Demand after switching to guarantee progress.
                return ClusterType.ON_DEMAND
            else:
                # Wait for spot in the current region, using On-Demand to make progress.
                return ClusterType.ON_DEMAND