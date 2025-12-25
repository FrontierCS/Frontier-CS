import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cant_be_late_multi_v1"  # REQUIRED: unique identifier

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

        # Internal state: whether we've committed to always using on-demand
        self._commit_on_demand = False

        # Precompute a conservative safety margin:
        # one full step (gap) plus twice the restart overhead
        # (covers existing + future restart overheads).
        self._safety_margin = self.env.gap_seconds + 2.0 * self.restart_overhead

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Sum of completed work so far
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining_work = max(0.0, self.task_duration - done)

        # If task is already finished, don't run any more compute
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds

        # If we have already committed, keep using on-demand
        if self._commit_on_demand:
            return ClusterType.ON_DEMAND

        # Determine whether we can afford to "gamble" one more step
        # on spot (or waiting) without risking the deadline.
        # We only gamble if, after potentially wasting one full gap
        # with zero progress, we can still finish the remaining work
        # plus at most ~2*restart_overhead time.
        if time_left <= remaining_work + self._safety_margin:
            # Not enough slack to keep waiting or relying on spot:
            # commit to on-demand from now on.
            self._commit_on_demand = True
            return ClusterType.ON_DEMAND

        # We are safely far from the deadline: use Spot if available,
        # otherwise wait (no cluster) to avoid expensive on-demand.
        if has_spot:
            return ClusterType.SPOT

        # No spot available and plenty of slack: pause to wait for spot.
        return ClusterType.NONE
