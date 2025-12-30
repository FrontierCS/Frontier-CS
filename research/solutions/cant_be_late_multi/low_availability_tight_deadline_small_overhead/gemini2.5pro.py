import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"

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

        self.availability = self.env.traces

        if not self.availability or not self.availability[0]:
            self.max_trace_len = 0
            self.region_scores = []
            self.sorted_regions = []
        else:
            self.max_trace_len = len(self.availability[0])
            self.region_scores = [
                sum(trace) / len(trace) if trace else 0
                for trace in self.availability
            ]
            self.sorted_regions = sorted(
                range(self.env.get_num_regions()),
                key=lambda r: self.region_scores[r],
                reverse=True
            )

        self.wait_threshold = 3600.0

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
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        time_elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - time_elapsed

        on_demand_time_needed = work_remaining + self.restart_overhead

        if time_remaining <= on_demand_time_needed:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if self.max_trace_len > 0:
            current_region = self.env.get_current_region()

            current_timestep = min(
                int(time_elapsed / self.env.gap_seconds),
                self.max_trace_len - 1
            )

            for region_idx in self.sorted_regions:
                if region_idx == current_region:
                    continue

                if self.availability[region_idx][current_timestep]:
                    self.env.switch_region(region_idx)
                    return ClusterType.SPOT

        slack = time_remaining - on_demand_time_needed
        if slack > self.wait_threshold:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND