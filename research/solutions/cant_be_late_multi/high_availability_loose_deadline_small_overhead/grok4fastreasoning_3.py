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
        trace_files = config.get("trace_files", [])
        self.num_regions = len(trace_files)
        self.traces = []
        self.streaks = []
        for path in trace_files:
            with open(path, 'r') as tf:
                trace = json.load(tf)
            self.traces.append(trace)
            L = len(trace)
            streak = [0] * L
            for tt in range(L - 1, -1, -1):
                if trace[tt]:
                    streak[tt] = 1 + (streak[tt + 1] if tt + 1 < L else 0)
            self.streaks.append(streak)

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
        if not hasattr(self, 'traces') or not self.traces:
            # Fallback if no traces
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        curr_r = self.env.get_current_region()
        gap = self.env.gap_seconds
        elapsed = self.env.elapsed_seconds
        t = int(elapsed // gap)
        num_r = self.env.get_num_regions()

        candidates = []
        for r in range(num_r):
            trace = self.traces[r]
            streak = self.streaks[r]
            if t < len(trace) and trace[t]:
                k = streak[t] if t < len(streak) else 1
                candidates.append((k, r))

        if not candidates:
            return ClusterType.ON_DEMAND

        max_k = max(k for k, r in candidates)
        best_rs = [r for k, r in candidates if k == max_k]
        if curr_r in best_rs:
            best_r = curr_r
        else:
            best_r = min(best_rs)

        if best_r != curr_r:
            self.env.switch_region(best_r)

        return ClusterType.SPOT