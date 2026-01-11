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
        self.num_regions = len(config.get("trace_files", []))
        for path in config["trace_files"]:
            with open(path, 'r') as tf:
                data = json.load(tf)
                trace = [bool(x) for x in data]
                self.traces.append(trace)
        self.gap_seconds = self.env.gap_seconds
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
        if not self.traces or self.num_regions == 0:
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        current_step = int(elapsed // self.gap_seconds)
        trace_len = len(self.traces[0]) if self.traces else 0

        if current_step >= trace_len:
            return ClusterType.ON_DEMAND

        # Check if current has spot
        current_has_spot = self.traces[current_region][current_step]

        if current_has_spot:
            return ClusterType.SPOT

        # Find best region with spot: longest streak starting now
        best_r = current_region
        best_streak = 0
        for r in range(self.num_regions):
            if self.traces[r][current_step]:
                streak = 1
                s = current_step + 1
                while s < trace_len and self.traces[r][s]:
                    streak += 1
                    s += 1
                if streak > best_streak:
                    best_streak = streak
                    best_r = r

        if best_streak > 0:
            if best_r != current_region:
                self.env.switch_region(best_r)
            return ClusterType.SPOT
        else:
            # No spot anywhere, use ON_DEMAND in current region
            return ClusterType.ON_DEMAND