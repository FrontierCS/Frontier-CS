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

        # Internal state
        self.force_on_demand = False

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """

        # Ensure attribute exists even if solve() wasn't called for some reason
        if not hasattr(self, "force_on_demand"):
            self.force_on_demand = False

        # Compute remaining work in seconds
        total_done = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining_work = self.task_duration - total_done
        if remaining_work <= 1e-6:
            # Task is effectively done; no need to run more
            return ClusterType.NONE

        # If we've already hit or passed the deadline, just stop
        if self.env.elapsed_seconds >= self.deadline:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        gap = getattr(self.env, "gap_seconds", 1.0)
        restart_overhead = self.restart_overhead

        # If we've already decided to stick with On-Demand, keep doing so
        if self.force_on_demand:
            return ClusterType.ON_DEMAND

        # Safety check: if even switching to On-Demand now may not finish in time,
        # we still switch to On-Demand to minimize lateness.
        if remaining_work + restart_overhead >= time_left - 1e-6:
            self.force_on_demand = True
            return ClusterType.ON_DEMAND

        # Decide whether we can safely delay committing to On-Demand by one more step.
        # Worst-case if we delay:
        #   - We lose one entire gap of time.
        #   - We may incur up to two restart overheads in total (one from a possible
        #     preemption on Spot during this step and one when switching to On-Demand),
        #     but due to "no stacking", at most 2 * restart_overhead extra time.
        # So we require:
        #   current_time + gap + 2 * R + remaining_work <= deadline
        # => remaining_work + 2 * R + gap <= time_left
        if remaining_work + 2.0 * restart_overhead + gap >= time_left - 1e-6:
            # Cannot safely wait; commit to On-Demand now and stick with it.
            self.force_on_demand = True
            return ClusterType.ON_DEMAND

        # Safe to delay committing to On-Demand: use Spot when available, else idle.
        if has_spot:
            return ClusterType.SPOT

        # No Spot right now, but still have enough slack to wait.
        return ClusterType.NONE
