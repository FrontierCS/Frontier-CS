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
        self.num_regions = len(config["trace_files"])
        self.traces = []
        for tf in config["trace_files"]:
            with open(tf, 'r') as tf_file:
                raw = json.load(tf_file)
                trace = [bool(x) for x in raw]
            self.traces.append(trace)

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
        t = int(self.env.elapsed_seconds // self.env.gap_seconds)

        best_r = -1
        best_streak = -1

        for r in range(self.num_regions):
            if t >= len(self.traces[r]):
                continue
            if not self.traces[r][t]:
                continue
            # Compute streak
            streak = 0
            tt = t
            while tt < len(self.traces[r]) and self.traces[r][tt]:
                streak += 1
                tt += 1
            # Prefer longer streak, or same streak but current region
            if streak > best_streak or (streak == best_streak and r == current_region):
                best_streak = streak
                best_r = r

        if best_r != -1:
            if best_r != current_region:
                self.env.switch_region(best_r)
            return ClusterType.SPOT
        else:
            # No spot available anywhere, use ON_DEMAND
            return ClusterType.ON_DEMAND