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

        # Load availability traces
        self.gap = self.env.gap_seconds
        self.num_regions = self.env.get_num_regions()
        trace_files = config["trace_files"]
        self.availability = []
        for path in trace_files:
            with open(path, 'r') as f:
                trace = json.load(f)
                self.availability.append([bool(x) for x in trace])
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
        step_idx = int(self.env.elapsed_seconds // self.gap)
        done_work = sum(self.task_done_time)
        remaining_work = self.task_duration - done_work
        time_left = self.deadline - self.env.elapsed_seconds

        # Safety check: if not enough time even for on-demand, use it
        if time_left < remaining_work + self.restart_overhead * 2 + self.gap:
            return ClusterType.ON_DEMAND

        # Find best region with longest spot streak starting from now
        best_region = None
        best_streak = -1
        max_lookahead = min(10, int(time_left // self.gap))
        for r in range(self.num_regions):
            if step_idx >= len(self.availability[r]):
                continue
            if not self.availability[r][step_idx]:
                continue  # not available now
            streak = 0
            for s in range(step_idx, step_idx + max_lookahead):
                if s >= len(self.availability[r]) or not self.availability[r][s]:
                    break
                streak += 1
            if streak > best_streak:
                best_streak = streak
                best_region = r

        if best_region is not None:
            if best_region != current_region:
                self.env.switch_region(best_region)
            return ClusterType.SPOT
        else:
            # No spot available anywhere now, use on-demand
            return ClusterType.ON_DEMAND