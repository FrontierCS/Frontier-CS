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

        self.availability = []
        trace_files = config["trace_files"]
        self.num_regions = len(trace_files)
        for trace_path in trace_files:
            with open(trace_path, 'r') as tf:
                data = json.load(tf)
            if isinstance(data, list):
                self.availability.append(data)
            elif isinstance(data, dict) and "availability" in data:
                self.availability.append(data["availability"])
            else:
                raise ValueError(f"Invalid trace format in {trace_path}")
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
        current_time = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        current_step = int(current_time // gap)

        def score_region(r, start_step):
            if start_step >= len(self.availability[r]):
                return 0
            score = 0
            max_lookahead = 5
            for s in range(start_step, min(start_step + max_lookahead, len(self.availability[r]))):
                if self.availability[r][s]:
                    score += 1
            return score

        current_score = score_region(current_region, current_step)
        best_r = current_region
        best_score = current_score
        for r in range(self.num_regions):
            if r == current_region:
                continue
            sc = score_region(r, current_step)
            if sc > best_score:
                best_score = sc
                best_r = r

        switched = False
        if best_r != current_region and best_score > current_score:
            self.env.switch_region(best_r)
            switched = True

        # Update current_region after possible switch
        current_region = self.env.get_current_region()
        now_has_spot = False
        if current_step < len(self.availability[current_region]):
            now_has_spot = self.availability[current_region][current_step]

        if now_has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND