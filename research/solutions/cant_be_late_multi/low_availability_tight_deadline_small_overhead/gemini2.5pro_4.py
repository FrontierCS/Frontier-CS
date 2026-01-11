import json
import math
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

        self.is_initialized = False
        self.GAMBLE_SLACK_THRESHOLD = 6.0 * 3600

        self.region_stats = None
        self.total_steps_overall = 0
        return self

    def _initialize(self):
        """One-time initialization on the first step."""
        num_regions = self.env.get_num_regions()
        self.region_stats = {
            i: {'up_steps': 0, 'total_steps': 0} for i in range(num_regions)
        }
        self.is_initialized = True

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
        if not self.is_initialized:
            self._initialize()

        self.total_steps_overall += 1

        current_region = self.env.get_current_region()
        self.region_stats[current_region]['total_steps'] += 1
        if has_spot:
            self.region_stats[current_region]['up_steps'] += 1

        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        time_needed_guaranteed = work_remaining + self.restart_overhead

        if time_left <= time_needed_guaranteed:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        slack = time_left - time_needed_guaranteed

        if slack <= self.GAMBLE_SLACK_THRESHOLD:
            return ClusterType.ON_DEMAND
        else:
            num_regions = self.env.get_num_regions()
            best_region = -1

            unexplored_region = -1
            for r in range(num_regions):
                if r != current_region and self.region_stats[r]['total_steps'] == 0:
                    unexplored_region = r
                    break
            
            if unexplored_region != -1:
                best_region = unexplored_region
            else:
                max_ucb_score = -1.0
                N = self.total_steps_overall
                for r in range(num_regions):
                    if r == current_region:
                        continue
                    
                    stats = self.region_stats[r]
                    n_r = stats['total_steps']
                    
                    p_hat_r = stats['up_steps'] / n_r
                    exploration_term = math.sqrt(2 * math.log(N) / n_r)
                    ucb_score = p_hat_r + exploration_term

                    if ucb_score > max_ucb_score:
                        max_ucb_score = ucb_score
                        best_region = r

            if best_region == -1:
                return ClusterType.ON_DEMAND
            else:
                self.env.switch_region(best_region)
                return ClusterType.NONE