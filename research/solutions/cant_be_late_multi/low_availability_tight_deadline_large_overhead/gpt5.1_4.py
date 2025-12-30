import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy using spot-first then on-demand fallback."""

    NAME = "my_strategy"

    def solve(self, spec_path: str) -> "Solution":
        """Initialize the solution from spec_path config."""
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Internal strategy state
        self._mode_spot_first = 0  # 0: prefer spot, 1: committed to on-demand
        self._mode = self._mode_spot_first
        self._base_region = 0  # stick to initial region; avoid region-switch overheads

        # Track accumulated work efficiently without re-summing full list
        self._work_done = 0.0
        self._last_task_done_len = 0

        # Conservative safety guard time (seconds) when deciding to commit to on-demand
        # Use ~3 hours or 3 * overhead, whichever is larger
        three_hours = 3 * 3600.0
        self._commit_guard = max(3 * self.restart_overhead, three_hours)

        return self

    def _update_work_done(self) -> None:
        """Incrementally update accumulated work from task_done_time list."""
        td = self.task_done_time
        n = len(td)
        if n > self._last_task_done_len:
            # Sum only new segments
            s = 0.0
            for i in range(self._last_task_done_len, n):
                s += td[i]
            self._work_done += s
            self._last_task_done_len = n

    def _should_commit_to_ondemand(self, time_left: float, work_remaining: float) -> bool:
        """Decide if we must switch to on-demand to safely meet deadline."""
        # Time needed if we switch to on-demand now (worst case: pay full restart_overhead once)
        needed_time = work_remaining + self.restart_overhead
        # Commit when remaining slack is no more than needed_time plus a guard buffer
        return time_left <= needed_time + self._commit_guard

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """Decide next action based on current state."""
        # Update internal work accounting
        self._update_work_done()

        # If already completed, do nothing further
        work_remaining = self.task_duration - self._work_done
        if work_remaining <= 0:
            return ClusterType.NONE

        # Basic time bookkeeping
        time_elapsed = self.env.elapsed_seconds
        time_left = self.deadline - time_elapsed

        # Hard fail-safe: if somehow past deadline, just use on-demand
        if time_left <= 0:
            return ClusterType.ON_DEMAND

        # Once committed, always use on-demand
        if self._mode != self._mode_spot_first:
            return ClusterType.ON_DEMAND

        # Still in spot-first phase: check if it's time to commit to on-demand
        if self._should_commit_to_ondemand(time_left, work_remaining):
            self._mode = 1  # committed to on-demand
            return ClusterType.ON_DEMAND

        # Spot-first phase and still safe to gamble on spot
        if has_spot:
            # Prefer running on spot when available
            return ClusterType.SPOT

        # Spot not available and not yet time to commit: wait (no cost, spend slack)
        return ClusterType.NONE