import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cant-Be-Late Multi-Region Scheduling Strategy."""

    NAME = "cant_be_late_multi_region_v1"

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

        # Cache scalar parameters (in seconds) to avoid repeated conversions/lookups.
        # Fallbacks are defensive; primary attributes follow the problem spec.
        duration_attr = getattr(self, "task_duration", None)
        if duration_attr is None:
            duration_attr = getattr(self, "task_durations", None)
        if isinstance(duration_attr, (list, tuple)):
            duration_attr = duration_attr[0]
        self._duration = float(duration_attr)

        overhead_attr = getattr(self, "restart_overhead", None)
        if overhead_attr is None:
            overhead_attr = getattr(self, "restart_overheads", None)
        if isinstance(overhead_attr, (list, tuple)):
            overhead_attr = overhead_attr[0]
        self._restart_overhead = float(overhead_attr)

        deadline_attr = getattr(self, "deadline", None)
        if deadline_attr is None:
            deadline_attr = getattr(self, "deadline_seconds", None)
        if isinstance(deadline_attr, (list, tuple)):
            deadline_attr = deadline_attr[0]
        self._deadline = float(deadline_attr)

        # Internal flag: once we commit to On-Demand, stay on it.
        self._committed_to_on_demand = False

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Amount of work completed so far (seconds)
        done_time_list = getattr(self, "task_done_time", None)
        if done_time_list:
            done = float(sum(done_time_list))
        else:
            done = 0.0

        remaining = self._duration - done
        if remaining <= 0.0:
            # Task finished; no need to run further.
            return ClusterType.NONE

        env = self.env
        time_left = self._deadline - float(env.elapsed_seconds)

        # If somehow past deadline, still try to finish on On-Demand.
        if time_left <= 0.0:
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        gap = float(env.gap_seconds)
        overhead = self._restart_overhead

        # Slack: extra wall-clock time beyond the minimum required to finish
        # assuming at most one more restart overhead once we commit to On-Demand.
        slack = time_left - (remaining + overhead)

        # Conservative bound on how much slack can decrease in a single step:
        # one full gap plus at most one restart overhead.
        max_slack_drop_per_step = gap + overhead

        # Commit decision: once slack is small enough that one bad step could
        # eliminate it, switch permanently to On-Demand.
        if not self._committed_to_on_demand:
            if slack <= max_slack_drop_per_step:
                self._committed_to_on_demand = True

        if self._committed_to_on_demand:
            return ClusterType.ON_DEMAND

        # Cost-sensitive phase (not yet committed to On-Demand)

        # Prefer Spot whenever it is available.
        if has_spot:
            return ClusterType.SPOT

        # Spot is unavailable.
        # If we still have plenty of slack, we can afford to wait (NONE).
        # Use a slightly larger margin (2 * max_slack_drop_per_step) here so we
        # don't risk long Spot outages late in the schedule.
        if slack >= 2.0 * max_slack_drop_per_step:
            return ClusterType.NONE

        # Slack is getting tight and Spot is unavailable: switch to On-Demand
        # and stay there.
        self._committed_to_on_demand = True
        return ClusterType.ON_DEMAND
