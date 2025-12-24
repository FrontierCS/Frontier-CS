import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy focusing on cheap Spot usage with safe On-Demand fallback."""

    NAME = "cb_late_multi_region_v1"

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

        # Runtime strategy parameters (initialized later when env is available)
        self._initialized_runtime_params = False
        self._committed_to_on_demand = False
        self._safe_slack_seconds = None
        self._fudge_seconds = None

        return self

    def _initialize_runtime_params(self):
        """Lazy initialization of runtime parameters once env is ready."""
        # Safety buffer beyond strict minimum time needed on On-Demand (in seconds)
        # Using a conservative 2 hours to comfortably cover discretization and modeling inaccuracies.
        self._safe_slack_seconds = 2 * 3600.0

        # Fudge factor to account for discretization / step rounding:
        # ensure it's at least one step and at least one restart_overhead.
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        self._fudge_seconds = max(gap, float(self.restart_overhead))

        self._committed_to_on_demand = False
        self._initialized_runtime_params = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        if not self._initialized_runtime_params:
            self._initialize_runtime_params()

        # Compute remaining work and time.
        work_done = sum(self.task_done_time) if self.task_done_time else 0.0
        work_remaining = max(self.task_duration - work_done, 0.0)
        time_remaining = self.deadline - self.env.elapsed_seconds

        # If no work left or no time left, don't run anything.
        if work_remaining <= 0.0 or time_remaining <= 0.0:
            return ClusterType.NONE

        # If we haven't yet committed to On-Demand, check if we should.
        if not self._committed_to_on_demand:
            # Upper bound on time needed to safely finish on On-Demand from now.
            # Includes one full restart overhead and a discretization fudge factor.
            time_needed_bound = work_remaining + self.restart_overhead + self._fudge_seconds
            slack = time_remaining - time_needed_bound

            # Commit to On-Demand when slack gets small: from this point on,
            # always use On-Demand to guarantee completion.
            if slack <= self._safe_slack_seconds:
                self._committed_to_on_demand = True

        # If committed to On-Demand, always run on it.
        if self._committed_to_on_demand:
            return ClusterType.ON_DEMAND

        # Pre-commit phase: prefer Spot when available; otherwise, idle.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable and we're still in the flexible phase: idle to save cost,
        # relying on large slack and future Spot availability.
        return ClusterType.NONE
