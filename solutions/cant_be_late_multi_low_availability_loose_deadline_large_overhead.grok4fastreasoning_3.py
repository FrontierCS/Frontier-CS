import json
from argparse import Namespace
from typing import List

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

        # Load traces
        self.num_regions = len(config["trace_files"])
        self.avail: List[List] = []
        for fpath in config["trace_files"]:
            with open(fpath, 'r') as tf:
                trace = json.load(tf)
            self.avail.append(trace)
        # Assume all traces have the same length
        self.num_steps = len(self.avail[0]) if self.avail else 0

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
        done = sum(self.task_done_time)
        if done >= self.task_duration:
            return ClusterType.NONE

        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        current_step = int(elapsed // gap)
        remaining_work = self.task_duration - done
        remaining_time = self.deadline - elapsed
        effective_remaining_time = remaining_time - self.remaining_restart_overhead

        if effective_remaining_time <= 0:
            return ClusterType.NONE

        # Find best region with spot available now, preferring longest streak
        best_r = -1
        best_streak = 0
        for r in range(self.num_regions):
            if current_step >= len(self.avail[r]):
                continue
            if self.avail[r][current_step]:
                streak = 0
                t = current_step
                while t < len(self.avail[r]) and self.avail[r][t]:
                    streak += 1
                    t += 1
                if streak > best_streak:
                    best_streak = streak
                    best_r = r

        if best_r != -1:
            if best_r != current_region:
                self.env.switch_region(best_r)
            return ClusterType.SPOT
        else:
            # No spot available anywhere now
            # Check if we can wait for spot in some region
            min_wait = float('inf')
            best_future_r = -1
            for r in range(self.num_regions):
                for w in range(1, 10):  # Check up to 9 steps ahead
                    fs = current_step + w
                    if fs < len(self.avail[r]) and self.avail[r][fs]:
                        if w < min_wait:
                            min_wait = w
                            best_future_r = r
                        break

            can_wait = (min_wait < float('inf') and
                        min_wait * gap + remaining_work <= effective_remaining_time)
            if can_wait:
                if best_future_r != current_region:
                    self.env.switch_region(best_future_r)
                return ClusterType.NONE
            else:
                # Cannot afford to wait, use on-demand
                return ClusterType.ON_DEMAND
