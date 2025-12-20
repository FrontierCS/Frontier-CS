import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cant-Be-Late Multi-Region Scheduling Strategy."""

    NAME = "cant_be_late_v1"

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

        # Internal tracking of accumulated useful work (seconds).
        self._work_done = 0.0
        self._last_task_done_index = 0

        # Once we commit to on-demand (for deadline safety), never go back.
        self._commit_to_on_demand = False

        return self

    def _update_work_done(self) -> None:
        """Incrementally track total completed work to avoid O(n) per step."""
        td = self.task_done_time
        idx = self._last_task_done_index
        if idx < len(td):
            new_sum = 0.0
            for v in td[idx:]:
                new_sum += v
            self._work_done += new_sum
            self._last_task_done_index = len(td)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Update internal accounting of completed work.
        self._update_work_done()

        remaining_work = self.task_duration - self._work_done
        if remaining_work <= 0.0:
            # Task is already complete; no need to run further.
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed

        # If somehow past the deadline, just keep running on-demand.
        if time_left <= 0.0:
            self._commit_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Slack is how much wall-clock we can still waste and still finish
        # if we ran at full speed from now on.
        slack = time_left - remaining_work

        # Safety threshold on slack: we must leave enough time to switch
        # to on-demand and absorb one restart overhead, plus a small buffer
        # for step granularity.
        gap = getattr(self.env, "gap_seconds", 1.0)
        c = self.restart_overhead
        threshold_slack = c + 2.0 * gap

        if not self._commit_to_on_demand:
            if slack <= threshold_slack:
                # From now on, stick to on-demand to ensure we meet deadline.
                self._commit_to_on_demand = True

        if self._commit_to_on_demand:
            return ClusterType.ON_DEMAND

        # Opportunistic spot usage phase.
        if has_spot:
            return ClusterType.SPOT

        # No spot available and plenty of slack left: wait to save cost.
        return ClusterType.NONE
