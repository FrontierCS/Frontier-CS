import json
from argparse import Namespace
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "greedy_streak"

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

        # Load traces assuming each is a JSON list of 0/1 or booleans
        self.traces: List[List[bool]] = []
        trace_files = config.get("trace_files", [])
        for path in trace_files:
            with open(path, "r") as f:
                trace_data = json.load(f)
            if isinstance(trace_data, dict) and "availability" in trace_data:
                trace = [bool(x) for x in trace_data["availability"]]
            else:
                trace = [bool(x) for x in trace_data]
            self.traces.append(trace)

        self.num_regions = len(self.traces)
        self.step = 0
        if self.num_regions > 0:
            self.num_steps = len(self.traces[0])
            self.streaks = [[0] * self.num_steps for _ in range(self.num_regions)]
            for r in range(self.num_regions):
                for t in range(self.num_steps - 1, -1, -1):
                    if self.traces[r][t]:
                        next_streak = self.streaks[r][t + 1] if t + 1 < self.num_steps else 0
                        self.streaks[r][t] = 1 + next_streak
                    else:
                        self.streaks[r][t] = 0
        else:
            self.num_steps = 0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        total_done = sum(self.task_done_time)
        if total_done >= self.task_duration:
            return ClusterType.NONE

        t = self.step
        self.step += 1

        current_region = self.env.get_current_region()

        best_region = -1
        best_streak = -1
        for r in range(self.num_regions):
            if t >= self.num_steps:
                streak = 0
            else:
                streak = self.streaks[r][t]
            if streak > best_streak:
                best_streak = streak
                best_region = r

        if best_streak > 0:
            if best_region != current_region:
                self.env.switch_region(best_region)
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND