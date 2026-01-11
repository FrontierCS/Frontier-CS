import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cb_late_mr_heuristic_v1"

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

        # Internal state
        self._locked_od = False
        self._cached_done_len = 0
        self._cached_done_sum = 0.0

        # Handle potential enum naming differences
        self._NONE = getattr(ClusterType, "NONE", getattr(ClusterType, "None"))
        self._OD = getattr(ClusterType, "ON_DEMAND")
        self._SPOT = getattr(ClusterType, "SPOT")

        return self

    def _update_progress_cache(self):
        # Incrementally update cached sum of task_done_time to avoid O(n) per-step summations.
        td = self.task_done_time
        if td is None:
            return
        n = len(td)
        if n > self._cached_done_len:
            # Sum only the new segments appended since last check
            add = 0.0
            for i in range(self._cached_done_len, n):
                add += td[i]
            self._cached_done_sum += add
            self._cached_done_len = n

    def _remaining_work_seconds(self) -> float:
        # Compute remaining work in seconds using cached sum
        self._update_progress_cache()
        rem = self.task_duration - self._cached_done_sum
        if rem < 0.0:
            rem = 0.0
        return rem

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we've already decided to finish on on-demand, stick to it.
        if self._locked_od:
            return self._OD

        # Compute basic quantities
        now = self.env.elapsed_seconds
        deadline = self.deadline
        time_left = deadline - now

        # If already done, no need to run anything.
        rem_work = self._remaining_work_seconds()
        if rem_work <= 0.0:
            return self._NONE

        # Determine the minimal time to finish if committing to on-demand now.
        # If we're already on on-demand, account for any remaining restart overhead;
        # otherwise, switching to OD incurs a fresh restart overhead.
        overhead_remaining = self.remaining_restart_overhead if last_cluster_type == self._OD else self.restart_overhead
        if overhead_remaining < 0.0:
            overhead_remaining = 0.0
        t_od_now = rem_work + overhead_remaining

        # Safety guard to handle discrete steps and minor rounding issues.
        # Commit to OD if the remaining time is tight.
        gap = getattr(self.env, "gap_seconds", 0.0)
        commit_guard = gap + 1.0  # add 1s fudge
        if time_left <= t_od_now + commit_guard:
            self._locked_od = True
            return self._OD

        # Otherwise, prefer spot whenever available; if not, pause to save cost.
        if has_spot:
            return self._SPOT
        else:
            return self._NONE