import json
from argparse import Namespace
from collections import deque

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "UrgencyBasedMultiRegion"  # REQUIRED: unique identifier

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

        # Custom initialization for the strategy's state
        self.first_step = True
        self.num_regions = 0
        self.region_spot_history = []
        
        # Hyperparameters
        self.HISTORY_WINDOW = 24
        self.HIGH_URGENCY_THRESHOLD = 0.8
        self.SWITCH_AVAIL_THRESHOLD = 0.8

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Initialization on the first step to get environment details
        if self.first_step:
            self.num_regions = self.env.get_num_regions()
            # Use deque for efficient O(1) appends and pops.
            # Start with an optimistic history ([1]) to encourage initial exploration.
            self.region_spot_history = [
                deque([1], maxlen=self.HISTORY_WINDOW) for _ in range(self.num_regions)
            ]
            self.first_step = False

        # 1. STATE UPDATE
        current_region = self.env.get_current_region()
        self.region_spot_history[current_region].append(1 if has_spot else 0)

        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        # 2. HANDLE COMPLETION
        # If the task is finished, do nothing to save cost.
        if work_remaining <= 0:
            return ClusterType.NONE

        # 3. URGENCY CALCULATION
        # Effective time left until the deadline, accounting for any pending restart overhead.
        effective_time_left = self.deadline - self.env.elapsed_seconds - self.remaining_restart_overhead
        # Time needed to finish if we use on-demand, with a buffer for one potential future restart.
        work_with_buffer = work_remaining + self.restart_overhead

        if effective_time_left <= 1e-9:  # Avoid division by zero.
            urgency = float('inf')
        else:
            urgency = work_with_buffer / effective_time_left

        # 4. DECISION LOGIC
        
        # 4.1. PANIC MODE (Urgency >= 1.0)
        # Not enough time left for anything but On-Demand.
        if urgency >= 1.0:
            return ClusterType.ON_DEMAND

        # 4.2. BEST CASE (Spot is available)
        # If spot is available and we are not in panic mode, use it.
        if has_spot:
            return ClusterType.SPOT

        # 4.3. CHALLENGING CASE (Spot is NOT available)
        
        # 4.3.1. HIGH URGENCY
        # Slack is low. Use On-Demand to make guaranteed progress.
        if urgency > self.HIGH_URGENCY_THRESHOLD:
            return ClusterType.ON_DEMAND
        
        # 4.3.2. LOW URGENCY
        # Plenty of slack. We can afford to wait or explore.
        else:
            # Evaluate switching to a region with better historical spot availability.
            availabilities = [sum(h) / len(h) if h else 0.0 for h in self.region_spot_history]
            
            best_region_idx = -1
            max_avail = -1.0
            for i, avail in enumerate(availabilities):
                if avail > max_avail:
                    max_avail = avail
                    best_region_idx = i

            # If a significantly better region exists, switch to it.
            if (best_region_idx != -1 and
                    best_region_idx != current_region and
                    max_avail >= self.SWITCH_AVAIL_THRESHOLD):
                
                self.env.switch_region(best_region_idx)
                # After switching, we don't know the new region's spot status.
                # Play it safe and wait one turn.
                return ClusterType.NONE
            else:
                # No promising region to switch to.
                # Since urgency is low, just wait for spot to become available.
                return ClusterType.NONE
