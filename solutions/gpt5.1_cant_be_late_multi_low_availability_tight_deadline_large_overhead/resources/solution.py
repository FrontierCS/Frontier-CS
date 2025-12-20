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

        # Custom internal state
        self._force_on_demand = False
        self._cum_done = 0.0  # cumulative completed work in seconds
        if hasattr(self, "task_done_time"):
            self._last_task_done_len = len(self.task_done_time)
            if self._last_task_done_len > 0:
                total = 0.0
                for v in self.task_done_time:
                    total += v
                self._cum_done = total
        else:
            self.task_done_time = []
            self._last_task_done_len = 0

        return self

    def _update_cum_done(self) -> None:
        """Incrementally track total work done to avoid repeated full summations."""
        tdt = self.task_done_time
        n = len(tdt)
        last_n = self._last_task_done_len
        if n > last_n:
            add = 0.0
            # Typically only one new segment is appended per step.
            for i in range(last_n, n):
                add += tdt[i]
            self._cum_done += add
            self._last_task_done_len = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update internal accounting of completed work.
        self._update_cum_done()

        remaining_work = self.task_duration - self._cum_done
        if remaining_work <= 0.0:
            # Task already finished.
            return ClusterType.NONE

        t_now = self.env.elapsed_seconds
        time_left = self.deadline - t_now

        # If we've already reached/passed the deadline but still have work,
        # run on-demand to minimize additional lateness.
        if time_left <= 0.0:
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        # Once we commit to on-demand, never go back to spot/none.
        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        gap = self.env.gap_seconds
        restart = self.restart_overhead

        # Safety check: can we afford to "risk" one more non-on-demand step?
        #
        # Worst-case for taking a non-on-demand step now:
        # - We gain no additional work this step (effective progress 0),
        # - Time advances by at most `gap`,
        # - Then we start on-demand, incurring one restart overhead,
        # - And we must still process all `remaining_work`.
        #
        # Ensure this worst-case still finishes before the deadline.
        if t_now + gap + restart + remaining_work > self.deadline:
            # It's no longer safe to risk: switch to on-demand permanently.
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        # Cost-saving phase: use spot whenever available, otherwise idle.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE
