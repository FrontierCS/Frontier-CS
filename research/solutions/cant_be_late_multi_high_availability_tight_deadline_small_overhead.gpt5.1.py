import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Safe-margin multi-region scheduling strategy."""

    NAME = "safe_margin_multi_region"

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

        # Store config in seconds for our own logic
        self._task_total_duration = float(config["duration"]) * 3600.0
        self._restart_overhead = float(config["overhead"]) * 3600.0
        self._deadline = float(config["deadline"]) * 3600.0

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Internal state for incremental tracking
        self._internal_initialized = False
        self._total_done = 0.0
        self._last_task_list_len = 0
        self._safety_margin = 0.0
        self._gap_seconds = None

        return self

    def _initialize_internal_state(self) -> None:
        """Initialize state that depends on the environment."""
        # Gap between decision steps
        self._gap_seconds = getattr(self.env, "gap_seconds", 0.0)

        # Worst-case wasted time in a single step (time elapsed minus work done)
        # We assume at most one restart overhead per step.
        self._safety_margin = self._gap_seconds + self._restart_overhead

        # Initialize progress tracking
        if self.task_done_time:
            self._total_done = float(sum(self.task_done_time))
            self._last_task_list_len = len(self.task_done_time)
        else:
            self._total_done = 0.0
            self._last_task_list_len = 0

        self._internal_initialized = True

    def _update_progress(self) -> None:
        """Incrementally update total work done based on task_done_time list."""
        current_len = len(self.task_done_time)
        if current_len > self._last_task_list_len:
            # Sum only newly added segments
            new_sum = 0.0
            for i in range(self._last_task_list_len, current_len):
                new_sum += self.task_done_time[i]
            self._total_done += new_sum
            self._last_task_list_len = current_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Lazy initialization once environment is attached
        if not self._internal_initialized:
            self._initialize_internal_state()
        else:
            self._update_progress()

        remaining_work = self._task_total_duration - self._total_done

        # If task is already complete, do not use any cluster
        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_left = self._deadline - elapsed

        # Compute slack: extra time beyond what is needed to finish on pure on-demand from now
        # under the worst-case assumption that we pay at most one restart overhead.
        slack = time_left - (remaining_work + self._restart_overhead)

        # If slack is small (or negative), commit to On-Demand to guarantee deadline.
        # We avoid SPOT/NONE when slack <= safety_margin to prevent falling behind
        # even under worst-case wasted time in the next step.
        if slack <= self._safety_margin:
            return ClusterType.ON_DEMAND

        # Plenty of slack: prefer Spot when available, otherwise pause (NONE) to save cost.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE