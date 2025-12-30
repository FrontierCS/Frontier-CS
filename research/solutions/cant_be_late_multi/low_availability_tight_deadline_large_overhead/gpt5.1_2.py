import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cant-Be-Late multi-region scheduling strategy."""

    NAME = "cant_be_late_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        deadline_hours = float(config["deadline"])
        duration_hours = float(config["duration"])
        overhead_hours = float(config["overhead"])

        args = Namespace(
            deadline_hours=deadline_hours,
            task_duration_hours=[duration_hours],
            restart_overhead_hours=[overhead_hours],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Convert key parameters to seconds from the initialized environment.
        # MultiRegionStrategy should have already converted hours -> seconds.
        self._deadline_seconds = float(self.deadline)
        self._task_total_duration = float(self.task_duration)
        self._restart_overhead_seconds = float(self.restart_overhead)

        # Safety margin: keep a buffer before deadline when we switch fully to on-demand.
        # Use up to 3 hours or half of slack, whichever is smaller.
        slack_seconds = max(0.0, self._deadline_seconds - self._task_total_duration)
        if slack_seconds <= 0.0:
            margin_seconds = 0.0
        else:
            max_margin_seconds = 3.0 * 3600.0
            margin_seconds = min(max_margin_seconds, 0.5 * slack_seconds)
        self.safety_margin_seconds = margin_seconds

        # State to track cumulative work done efficiently.
        self._work_done = 0.0
        self._last_task_done_len = 0

        # Once this flag is set, we exclusively use ON_DEMAND until completion.
        self._commit_to_on_demand = False

        return self

    def _update_work_done(self) -> None:
        """Incrementally update total work done from task_done_time segments."""
        segments = self.task_done_time
        cur_len = len(segments)
        if cur_len > self._last_task_done_len:
            # Sum only new segments appended since last call.
            new_work = sum(segments[self._last_task_done_len : cur_len])
            self._work_done += new_work
            self._last_task_done_len = cur_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Update cached work-done total.
        self._update_work_done()

        work_done = self._work_done
        if work_done >= self._task_total_duration:
            # Task already complete: no need to run anything.
            return ClusterType.NONE

        env = self.env
        elapsed = env.elapsed_seconds
        time_left = self._deadline_seconds - elapsed

        # If we're out of time, nothing sensible to do; but return NONE to avoid extra cost.
        if time_left <= 0.0:
            return ClusterType.NONE

        remaining_work = self._task_total_duration - work_done

        # Decide when to fully commit to on-demand.
        if not self._commit_to_on_demand:
            # Minimal time needed if we immediately switch to on-demand and never stop:
            # remaining work plus one restart overhead.
            min_required_time = remaining_work + self._restart_overhead_seconds

            # Commit when the remaining time is close to this bound (within safety margin).
            if time_left <= min_required_time + self.safety_margin_seconds:
                self._commit_to_on_demand = True

        # Once committed, stay on ON_DEMAND regardless of spot availability.
        if self._commit_to_on_demand:
            if self._work_done >= self._task_total_duration:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        # Pre-commit phase: be aggressive with spot to minimize cost.
        if has_spot:
            return ClusterType.SPOT

        # Spot not available and we still have ample slack before the commitment threshold:
        # wait (NONE) instead of paying for expensive on-demand now.
        return ClusterType.NONE