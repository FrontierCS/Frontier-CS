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
        # Track whether we've committed to always using on-demand.
        self.committed_to_on_demand = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Available attributes:
        - self.env.get_current_region(): Get current region index
        - self.env.get_num_regions(): Get total number of regions
        - self.env.switch_region(idx): Switch to region by index
        - self.env.elapsed_seconds: Current time elapsed
        - self.task_duration: Total task duration needed (seconds)
        - self.deadline: Deadline time (seconds)
        - self.restart_overhead: Restart overhead (seconds)
        - self.task_done_time: List of completed work segments
        - self.remaining_restart_overhead: Current pending overhead

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Total work completed so far.
        work_done = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining_work = self.task_duration - work_done

        # If task is done, don't run any more.
        if remaining_work <= 0:
            return ClusterType.NONE

        # Once we commit to on-demand, always stay there to avoid further restarts.
        if getattr(self, "committed_to_on_demand", False):
            return ClusterType.ON_DEMAND

        # Estimate whether switching to pure on-demand now can still meet the deadline.
        gap = getattr(self.env, "gap_seconds", 0.0)
        # Conservative estimate of restart overhead if we switch to on-demand now.
        overhead_if_switch = self.restart_overhead if last_cluster_type != ClusterType.ON_DEMAND else 0.0

        finishing_time_if_switch = self.env.elapsed_seconds + overhead_if_switch + remaining_work
        slack_if_switch = self.deadline - finishing_time_if_switch

        # Safety margin: at least two timesteps of slack to account for discrete decisions.
        safety_margin = 2.0 * gap

        # If slack is small, commit to on-demand to guarantee completion.
        if slack_if_switch <= safety_margin:
            self.committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Otherwise, we're still in the "spot-preferred" phase.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable and we still have plenty of slack: wait to save on on-demand cost.
        return ClusterType.NONE
