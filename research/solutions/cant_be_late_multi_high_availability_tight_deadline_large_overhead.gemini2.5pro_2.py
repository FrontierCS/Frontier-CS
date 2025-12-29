import json
import collections
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

        self.num_regions = self.env.get_num_regions()

        # Hyperparameters
        self.HISTORY_WINDOW = 24
        self.CRITICAL_BUFFER_SECONDS = self.restart_overhead
        self.SWITCH_SCORE_THRESHOLD = 0.80
        self.EXPLORE_HISTORY_THRESHOLD = 6

        # State tracking
        self.region_stats = {
            i: {'history': collections.deque(maxlen=self.HISTORY_WINDOW)}
            for i in range(self.num_regions)
        }
        self.unexplored_regions = set(range(self.num_regions))
        
        # Optimization to avoid re-calculating sum() over a long list.
        self.cached_work_done = 0.0
        self.last_task_done_time_len = 0

        return self

    def _get_score(self, region_idx: int) -> float:
        """Calculate the recent spot availability score for a region."""
        if region_idx in self.unexplored_regions:
            return 1.0

        history = self.region_stats[region_idx]['history']
        if not history:
            return 1.0

        return sum(history) / len(history)

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

        self.region_stats[current_region]['history'].append(1 if has_spot else 0)
        if current_region in self.unexplored_regions:
            if len(self.region_stats[current_region]['history']) >= self.EXPLORE_HISTORY_THRESHOLD:
                self.unexplored_regions.discard(current_region)

        if len(self.task_done_time) > self.last_task_done_time_len:
            self.cached_work_done += sum(self.task_done_time[self.last_task_done_time_len:])
            self.last_task_done_time_len = len(self.task_done_time)
        
        work_remaining = self.task_duration - self.cached_work_done
        if work_remaining <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        time_needed_for_od = work_remaining + self.restart_overhead
        
        if time_needed_for_od >= time_left - self.CRITICAL_BUFFER_SECONDS:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        
        target_region = -1
        
        unexplored_targets = self.unexplored_regions - {current_region}
        if unexplored_targets:
            target_region = sorted(list(unexplored_targets))[0]
        else:
            best_alt_score = -1.0
            best_alt_region = -1
            for r in range(self.num_regions):
                if r == current_region:
                    continue
                score = self._get_score(r)
                if score > best_alt_score:
                    best_alt_score = score
                    best_alt_region = r
            
            if best_alt_score > self.SWITCH_SCORE_THRESHOLD:
                target_region = best_alt_region

        if target_region != -1:
            is_switch_safe = (self.env.elapsed_seconds + self.restart_overhead + work_remaining) < self.deadline - self.CRITICAL_BUFFER_SECONDS
            if is_switch_safe:
                self.env.switch_region(target_region)
                return ClusterType.ON_DEMAND

        slack = time_left - work_remaining
        wait_threshold = self.restart_overhead + self.env.gap_seconds
        
        if slack > wait_threshold:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND