import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "streak_spot"

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
        for tf in config["trace_files"]:
            with open(tf, 'r') as tfh:
                self.traces.append(json.load(tfh))
        self.num_regions = len(self.traces)
        if self.num_regions == 0:
            self.num_regions = 1  # fallback
        self.max_steps = len(self.traces[0]) if self.traces else 0

        # Precompute streaks
        self.streaks = [[0 for _ in range(self.num_regions)] for _ in range(self.max_steps)]
        for r in range(self.num_regions):
            for s in range(self.max_steps - 1, -1, -1):
                if self.traces[r][s]:
                    k = 1
                    if s + 1 < self.max_steps:
                        k += self.streaks[s + 1][r]
                    self.streaks[s][r] = k
                else:
                    self.streaks[s][r] = 0

        self.step = 0
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
        current_step = self.step
        self.step += 1

        if current_step >= self.max_steps:
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()

        if self.traces[current_region][current_step]:
            return ClusterType.SPOT

        # Find candidates with spot now
        candidates = [r for r in range(self.num_regions) if self.traces[r][current_step]]

        if not candidates:
            return ClusterType.ON_DEMAND

        # Choose the one with longest streak
        best_r = max(candidates, key=lambda r: self.streaks[current_step][r])

        if best_r != current_region:
            self.env.switch_region(best_r)

        return ClusterType.SPOT