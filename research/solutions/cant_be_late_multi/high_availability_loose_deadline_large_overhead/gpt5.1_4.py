import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy focusing on spot usage with safe on-demand fallback."""

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

        # Internal strategy state
        self._commit_to_on_demand = False
        self._initialized_local = False
        self._gap_seconds = None

        return self

    def _ensure_initialized(self):
        if not self._initialized_local:
            # Cache gap_seconds for faster access
            self._gap_seconds = float(self.env.gap_seconds)
            self._initialized_local = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Strategy:
        - Use Spot whenever available while there is sufficient slack until deadline.
        - Once time slack (considering worst-case switch to On-Demand) becomes small,
          permanently switch to On-Demand-only to guarantee meeting the deadline.
        - Never use Spot when has_spot is False.
        """
        self._ensure_initialized()

        # Current progress and remaining work
        work_done = sum(self.task_done_time) if self.task_done_time else 0.0

        # If task already completed, run nothing to avoid extra cost.
        if work_done >= self.task_duration - 1e-6:
            return ClusterType.NONE

        remaining_work = self.task_duration - work_done
        remaining_time = self.deadline - self.env.elapsed_seconds

        # If there's no time left (should not usually happen), avoid extra cost.
        if remaining_time <= 0.0:
            return ClusterType.NONE

        # Decide whether to permanently commit to On-Demand.
        # Slack delta = remaining_time - (remaining_work + restart_overhead)
        # We commit when delta <= 2 * gap_seconds to guarantee completion by deadline,
        # even under discrete time steps and one restart overhead.
        if not self._commit_to_on_demand:
            delta = remaining_time - (remaining_work + self.restart_overhead)
            threshold = 2.0 * self._gap_seconds
            if delta <= threshold:
                self._commit_to_on_demand = True

        # If committed, always use On-Demand until completion.
        if self._commit_to_on_demand:
            return ClusterType.ON_DEMAND

        # Spot-first phase: use Spot if available; otherwise, wait.
        if has_spot:
            return ClusterType.SPOT

        # No Spot and not yet in On-Demand phase: pause to save cost.
        return ClusterType.NONE