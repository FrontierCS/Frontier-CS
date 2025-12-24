import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cant-Be-Late multi-region scheduling strategy."""

    NAME = "cant_be_late_safe_spot"

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
        self._force_on_demand = False
        self._work_done = 0.0
        self._last_td_len = 0

        return self

    def _update_work_done_cache(self) -> None:
        """Incrementally track total work done to avoid summing every step."""
        td = self.task_done_time
        length = len(td)
        if length > self._last_td_len:
            extra = 0.0
            for i in range(self._last_td_len, length):
                extra += td[i]
            self._work_done += extra
            self._last_td_len = length

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Strategy:
        - Before committing to on-demand:
          * Use Spot when available.
          * Otherwise, pause (NONE).
          * Ensure we always leave enough time to finish on on-demand only.
        - When it's no longer safe to waste another gap, commit to on-demand
          and stay there until completion.
        """
        # Update cached work done.
        self._update_work_done_cache()

        remaining_work = self.task_duration - self._work_done

        # If task is already finished, stop using any cluster.
        if remaining_work <= 0:
            self._force_on_demand = True
            return ClusterType.NONE

        # If we've already committed to on-demand, always use it.
        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        t = self.env.elapsed_seconds
        gap = self.env.gap_seconds

        # If even switching to on-demand now cannot meet the deadline,
        # we still choose on-demand to minimize lateness (though failure is unavoidable).
        min_finish_time_if_commit_now = t + self.restart_overhead + remaining_work
        if min_finish_time_if_commit_now > self.deadline:
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        # Check if it's safe to potentially waste the *next* gap with zero progress.
        # Worst case: we get no useful work in the next gap, then commit to on-demand.
        if t + gap + self.restart_overhead + remaining_work > self.deadline:
            # Not safe to delay further; commit to on-demand from now on.
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        # Exploration phase: use Spot when available, otherwise pause to avoid
        # unnecessary restarts and on-demand costs.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE
