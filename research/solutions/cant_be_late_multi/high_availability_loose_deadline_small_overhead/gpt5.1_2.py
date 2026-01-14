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

        # Internal state for efficient tracking
        self._runtime_initialized = False
        self._force_on_demand = False
        self._work_done_total = 0.0
        self._task_done_index = 0

        # Placeholders; real values set in _init_runtime()
        self._gap = None
        self._safety_buffer = None
        self._idle_slack_threshold = None

        return self

    def _init_runtime(self) -> None:
        """Lazy initialization of runtime-dependent parameters."""
        # gap_seconds is defined by the environment
        self._gap = float(self.env.gap_seconds)

        # Conservative safety buffer to account for restart overhead and discretization
        # Ensures we start on-demand early enough to finish before deadline.
        self._safety_buffer = float(self.restart_overhead + 2.0 * self._gap)

        # Threshold of "extra slack" under which we stop idling when Spot is unavailable
        # and start using On-Demand. Chosen as 25% of task duration or a few steps,
        # whichever is larger.
        idle_slack_fraction = 0.25  # 25% of task duration
        min_idle_slack = 4.0 * self._gap
        self._idle_slack_threshold = max(
            idle_slack_fraction * float(self.task_duration),
            min_idle_slack,
        )

        self._runtime_initialized = True

    def _update_work_done(self) -> float:
        """Incrementally update total work done to avoid O(n) sum each step."""
        idx = self._task_done_index
        tdt = self.task_done_time
        if len(tdt) > idx:
            total = self._work_done_total
            # Process only new segments since last call
            for i in range(idx, len(tdt)):
                total += tdt[i]
            self._work_done_total = total
            self._task_done_index = len(tdt)
        return self._work_done_total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Lazy initialization of runtime params that depend on env
        if not self._runtime_initialized:
            self._init_runtime()

        # Update work done efficiently
        work_done = self._update_work_done()
        remaining = self.task_duration - work_done
        if remaining <= 0.0:
            # Task already completed; no need to run any cluster.
            self._force_on_demand = False
            return ClusterType.NONE

        # Time metrics
        now = self.env.elapsed_seconds
        time_left = self.deadline - now

        # If somehow past deadline with remaining work, just use On-Demand.
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        # Ensure we don't go past deadline: commit to On-Demand when there is
        # only just enough time left to finish using pure On-Demand.
        if not self._force_on_demand:
            if time_left <= remaining + self._safety_buffer:
                self._force_on_demand = True

        # Once we commit to On-Demand, never go back to Spot.
        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        # Before commit phase: prefer Spot when available.
        if has_spot:
            return ClusterType.SPOT

        # No Spot available here; decide between idling and On-Demand
        slack = time_left - remaining  # extra time beyond required work

        # If slack is small, we can't afford to idle; use On-Demand.
        if slack <= self._idle_slack_threshold:
            return ClusterType.ON_DEMAND

        # Plenty of slack: wait (NONE) for cheaper Spot capacity to return.
        return ClusterType.NONE