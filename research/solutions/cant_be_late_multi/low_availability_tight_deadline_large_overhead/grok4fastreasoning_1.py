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

        # Load traces
        self.traces = []
        for tf in config.get("trace_files", []):
            with open(tf, 'r') as f:
                trace = json.load(f)
            self.traces.append(trace)

        if not self.traces:
            self.streak = []
            return self

        total_steps = len(self.traces[0])
        num_regions = len(self.traces)
        self.streak = [[0] * total_steps for _ in range(num_regions)]
        for r in range(num_regions):
            for t in range(total_steps - 1, -1, -1):
                if not self.traces[r][t]:
                    self.streak[r][t] = 0
                else:
                    next_streak = self.streak[r][t + 1] if t + 1 < total_steps else 0
                    self.streak[r][t] = 1 + next_streak

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
        if not hasattr(self, 'streak') or not self.streak:
            return ClusterType.ON_DEMAND

        current_r = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        current_t = int(elapsed // gap)
        total_steps = len(self.streak[0])
        if current_t >= total_steps:
            return ClusterType.NONE

        # Find best region with longest spot streak, prefer staying unless strictly better
        max_streak = self.streak[current_r][current_t]
        best_r = current_r
        num_regions = self.env.get_num_regions()
        for rr in range(num_regions):
            if rr == current_r:
                continue
            s = self.streak[rr][current_t]
            if s > max_streak:
                max_streak = s
                best_r = rr

        if best_r != current_r:
            self.env.switch_region(best_r)

        # Decide cluster type for best_r at current_t
        has_spot_new = self.traces[best_r][current_t]
        if has_spot_new:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND