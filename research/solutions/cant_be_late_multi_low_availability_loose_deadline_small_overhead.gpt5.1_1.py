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

        duration_hours = float(config["duration"])
        deadline_hours = float(config["deadline"])
        overhead_hours = float(config["overhead"])

        # Internal copies in seconds for our logic
        self._task_duration_seconds = duration_hours * 3600.0
        self._deadline_seconds = deadline_hours * 3600.0
        self._restart_overhead_seconds = overhead_hours * 3600.0

        args = Namespace(
            deadline_hours=deadline_hours,
            task_duration_hours=[duration_hours],
            restart_overhead_hours=[overhead_hours],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Strategy state
        self._runtime_initialized = False
        self._gap_seconds = None

        # Track cumulative work without O(n) summation every step
        self._cached_work_done = 0.0
        self._prev_done_len = 0

        # Once we commit to on-demand, we stay on-demand
        self.commit_on_demand = False

        return self

    def _initialize_runtime(self):
        if not self._runtime_initialized:
            # gap_seconds is provided by the environment in seconds
            self._gap_seconds = float(getattr(self.env, "gap_seconds", 3600.0))
            self._runtime_initialized = True

    def _update_work_done_cache(self):
        # Incrementally update cached sum of task_done_time
        tdt = self.task_done_time
        cur_len = len(tdt)
        if cur_len > self._prev_done_len:
            # Sum only newly appended segments
            new_segments = tdt[self._prev_done_len : cur_len]
            if new_segments:
                self._cached_work_done += float(sum(new_segments))
            self._prev_done_len = cur_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        self._initialize_runtime()
        self._update_work_done_cache()

        elapsed = float(self.env.elapsed_seconds)
        time_remaining = self._deadline_seconds - elapsed

        # If no time left, we cannot do anything meaningful.
        if time_remaining <= 0.0:
            return ClusterType.NONE

        # Remaining work (seconds)
        remaining_work = self._task_duration_seconds - self._cached_work_done
        if remaining_work <= 0.0:
            # Task already completed
            return ClusterType.NONE

        gap = self._gap_seconds
        restart_overhead = self._restart_overhead_seconds

        # Decide whether to commit to on-demand
        if not self.commit_on_demand:
            # Time required to finish if we commit to on-demand *now*
            required_time_if_commit_now = restart_overhead + remaining_work

            # If we take one more step without guaranteed progress (e.g., NONE or unlucky SPOT),
            # the remaining time would be (time_remaining - gap).
            # To stay safe, we only allow that if even then we can still finish on on-demand.
            if time_remaining - gap < required_time_if_commit_now:
                self.commit_on_demand = True

        # Once committed, always use on-demand to avoid any further risk.
        if self.commit_on_demand:
            return ClusterType.ON_DEMAND

        # Pre-commit phase: be aggressive with Spot, but never use On-Demand.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable and we still have plenty of slack: wait (no cost).
        return ClusterType.NONE
