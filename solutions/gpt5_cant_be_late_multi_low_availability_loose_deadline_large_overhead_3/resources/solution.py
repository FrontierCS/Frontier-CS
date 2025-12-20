import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "deadline_guard_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self._committed_to_od = False
        self._guard_steps = 1  # number of step-sized slack to keep before switching to OD

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
        self._committed_to_od = False
        return self

    def _remaining_work(self) -> float:
        return max(0.0, self.task_duration - sum(self.task_done_time))

    def _deadline_slack_after_switch_to_od_now(self, last_cluster_type: ClusterType) -> float:
        # Slack if we switch to OD now (worst-case guarantee time left after OD switch)
        overhead_to_start_od = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead
        time_remaining = self.deadline - self.env.elapsed_seconds
        remaining_work = self._remaining_work()
        return time_remaining - (overhead_to_start_od + remaining_work)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining_work = self._remaining_work()
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # If already committed to OD, continue using OD until finish.
        if self._committed_to_od or last_cluster_type == ClusterType.ON_DEMAND:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Decide if we must switch to OD now to guarantee meeting deadline.
        slack_if_switch_now = self._deadline_slack_after_switch_to_od_now(last_cluster_type)
        must_switch_to_od = False
        if slack_if_switch_now < 0.0:
            must_switch_to_od = True
        else:
            # Keep at least guard_steps worth of time steps of slack before attempting a risky step.
            required_slack = self.env.gap_seconds * float(self._guard_steps)
            if slack_if_switch_now < required_slack:
                must_switch_to_od = True

        if must_switch_to_od:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Safe to continue gambling on Spot.
        if has_spot:
            return ClusterType.SPOT

        # No Spot available; we can wait (NONE) to try again next step while we still have slack.
        return ClusterType.NONE
