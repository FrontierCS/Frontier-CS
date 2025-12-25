import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Slack-aware multi-region scheduling strategy."""

    NAME = "cbl_multi_slack_v1"

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

        # Once this flag is set, we always run on on-demand to avoid missing the deadline.
        self.force_on_demand = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Ensure flag exists even if solve() wasn't called as expected.
        if not hasattr(self, "force_on_demand"):
            self.force_on_demand = False

        # If somehow already past the deadline, just keep using on-demand.
        if self.env.elapsed_seconds >= self.deadline:
            return ClusterType.ON_DEMAND

        # Compute remaining work (in seconds).
        task_done_list = self.task_done_time or []
        done = float(sum(task_done_list))
        remaining_work = self.task_duration - done

        # If there is no remaining work, don't run any cluster.
        if remaining_work <= 0.0:
            return ClusterType.NONE

        remaining_time = self.deadline - self.env.elapsed_seconds
        gap = self.env.gap_seconds
        over = self.restart_overhead

        # If we've already committed to on-demand, always use it.
        if self.force_on_demand:
            return ClusterType.ON_DEMAND

        # Safety condition: it's safe to "risk" this step (by using SPOT or NONE)
        # only if, even in the worst case that this entire step provides zero
        # useful work and we then pay a full restart overhead, we can still
        # finish using only on-demand afterwards.
        #
        # Worst-case after risking this step:
        #   - time left: remaining_time - gap
        #   - work left: remaining_work
        #   - need at most: remaining_work + over
        safe_to_risk = (remaining_time - gap) >= (remaining_work + over)

        # If not safe to risk, permanently switch to on-demand from now on.
        if not safe_to_risk:
            self.force_on_demand = True
            return ClusterType.ON_DEMAND

        # We have enough slack to risk spot or idling.
        if has_spot:
            return ClusterType.SPOT

        # No spot available and we have slack: wait to save cost.
        return ClusterType.NONE
