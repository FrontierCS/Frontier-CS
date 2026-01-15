import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy focusing on cheap Spot usage with safe On-Demand fallback."""

    NAME = "cant_be_late_multi_region_basic_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Internal state for efficient tracking.
        self._force_on_demand = False
        self._done_work = 0.0
        self._last_task_done_len = 0

        return self

    def _update_done_work(self) -> None:
        """Incrementally track total completed work to avoid O(n) summations each step."""
        td_list = self.task_done_time
        current_len = len(td_list)
        if current_len > self._last_task_done_len:
            # Sum only the new segments since last step.
            self._done_work += sum(td_list[self._last_task_done_len:current_len])
            self._last_task_done_len = current_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update total done work.
        self._update_done_work()

        # Remaining work in seconds.
        remaining = self.task_duration - self._done_work
        if remaining <= 0.0:
            # Job already finished; no need to run anything.
            return ClusterType.NONE

        # If we've already committed to On-Demand, stick with it.
        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        time_elapsed = self.env.elapsed_seconds
        time_left = self.deadline - time_elapsed

        # If somehow we are at or beyond deadline, still try to finish on On-Demand.
        if time_left <= 0.0:
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
        overhead = self.restart_overhead

        # Conservative estimate of total wall-clock time needed to finish
        # if we switch to On-Demand now and never leave it.
        required_on_demand_time = overhead + remaining

        # Slack above the required On-Demand time.
        slack = time_left - required_on_demand_time

        # Commit margin: at least one step of slack so that, due to discrete timesteps,
        # we still commit while there is enough time left.
        margin = gap

        # If slack is getting small (<= margin), commit to On-Demand to guarantee completion.
        if slack <= margin:
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        # Spot phase: use Spot whenever available to minimize cost.
        if has_spot:
            return ClusterType.SPOT

        # No Spot available and still far from the hard deadline:
        # wait (NONE) and consume slack instead of paying for expensive On-Demand.
        return ClusterType.NONE