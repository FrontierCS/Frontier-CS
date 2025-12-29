import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy balancing Spot and On-Demand with deadline guarantees."""

    NAME = "cb_late_multiregion_v1"

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

        # Internal state for tracking progress and mode
        self._on_demand_committed = False
        self._last_task_done_len = 0
        self._work_done = 0.0
        self._initialized = False

        return self

    def _initialize_if_needed(self) -> None:
        if not self._initialized:
            # Cache key parameters (seconds)
            self._gap_seconds = float(self.env.gap_seconds)
            self._restart_overhead = float(self.restart_overhead)
            self._task_duration = float(self.task_duration)
            self._deadline_seconds = float(self.deadline)
            self._initialized = True

    def _update_work_done(self) -> None:
        """Incrementally track total work done to avoid O(n) summation each step."""
        cur_len = len(self.task_done_time)
        if cur_len > self._last_task_done_len:
            new_work = 0.0
            for i in range(self._last_task_done_len, cur_len):
                new_work += self.task_done_time[i]
            self._work_done += new_work
            self._last_task_done_len = cur_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        self._initialize_if_needed()
        self._update_work_done()

        # If the task is already finished, do nothing.
        if self._work_done >= self._task_duration:
            return ClusterType.NONE

        # If we've already committed to on-demand, stay there to avoid extra overhead.
        if self._on_demand_committed:
            return ClusterType.ON_DEMAND

        elapsed = self.env.elapsed_seconds
        slack = self._deadline_seconds - elapsed  # time left until deadline (seconds)

        # If somehow at or past deadline, best effort: run on-demand.
        if slack <= 0.0:
            self._on_demand_committed = True
            return ClusterType.ON_DEMAND

        remaining_work = self._task_duration - self._work_done

        # Safety check: can we afford one more "cheap" step (SPOT or NONE)
        # and still have enough time to finish remaining work on on-demand,
        # accounting for one restart_overhead?
        # Worst-case for a cheap step: we consume gap_seconds time and make no progress.
        can_afford_one_more_cheap_step = (
            (slack - self._gap_seconds) >= (remaining_work + self._restart_overhead)
        )

        if not can_afford_one_more_cheap_step:
            # Must commit to on-demand now to safely meet deadline.
            self._on_demand_committed = True
            return ClusterType.ON_DEMAND

        # We can still take at least one more cheap step.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: wait (NONE) to avoid on-demand cost while we have slack.
        return ClusterType.NONE