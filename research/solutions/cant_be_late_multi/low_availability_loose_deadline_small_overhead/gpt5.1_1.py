import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy focusing on meeting deadlines with low cost."""

    NAME = "my_strategy"

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

        # Cache scalar versions of key parameters (in seconds).
        td = getattr(self, "task_duration", None)
        if isinstance(td, (list, tuple)):
            self._task_duration = float(td[0])
        else:
            self._task_duration = float(td)

        dl = getattr(self, "deadline", None)
        if isinstance(dl, (list, tuple)):
            self._deadline = float(dl[0])
        else:
            self._deadline = float(dl)

        ro = getattr(self, "restart_overhead", None)
        if isinstance(ro, (list, tuple)):
            self._restart_overhead = float(ro[0])
        else:
            self._restart_overhead = float(ro)

        gap = getattr(self.env, "gap_seconds", 1.0)
        self._gap_seconds = float(gap) if gap is not None else 1.0

        # Initial slack relative to pure on-demand execution.
        self._initial_slack = max(self._deadline - self._task_duration, 0.0)

        # Safety buffer before the deadline to commit to on-demand.
        base_commit_buffer = max(3.0 * self._gap_seconds, 5.0 * self._restart_overhead)
        if self._initial_slack > 0.0:
            # Do not let the commit buffer be more than half of the total slack.
            self._commit_buffer = min(base_commit_buffer, 0.5 * self._initial_slack)
        else:
            self._commit_buffer = base_commit_buffer

        # Threshold of slack above which we are comfortable idling (NONE) when spot is down.
        idle_from_slack = 0.3 * self._initial_slack
        self._idle_slack_threshold = max(
            idle_from_slack,
            2.0 * self._commit_buffer,
            6.0 * self._gap_seconds,
        )

        # Incremental tracking of accumulated useful work.
        self._work_done = 0.0
        self._last_task_done_len = len(getattr(self, "task_done_time", []))

        # Once true, we always run on on-demand.
        self._committed_to_on_demand = False

        # Prefer region 0 if multiple regions exist; we otherwise ignore multi-region for robustness.
        try:
            if hasattr(self, "env") and hasattr(self.env, "get_num_regions"):
                num_regions = self.env.get_num_regions()
                if num_regions is not None and num_regions > 0:
                    self._preferred_region = 0
                    if hasattr(self.env, "switch_region"):
                        self.env.switch_region(self._preferred_region)
        except Exception:
            self._preferred_region = 0

        return self

    def _update_work_done(self) -> None:
        """Incrementally update total useful work done from task_done_time."""
        td_list = getattr(self, "task_done_time", None)
        if not td_list:
            self._work_done = 0.0
            self._last_task_done_len = 0
            return

        current_len = len(td_list)
        if current_len > self._last_task_done_len:
            # New segments appended since last check.
            new_segments = td_list[self._last_task_done_len:current_len]
            delta = 0.0
            for v in new_segments:
                delta += float(v)
            self._work_done += delta
            self._last_task_done_len = current_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Update internal view of completed work.
        self._update_work_done()

        remaining_work = self._task_duration - self._work_done
        if remaining_work <= 0.0:
            # Task complete.
            return ClusterType.NONE

        now = float(getattr(self.env, "elapsed_seconds", 0.0))
        time_left = self._deadline - now
        if time_left <= 0.0:
            # Deadline has passed; avoid incurring more cost.
            return ClusterType.NONE

        R = self._restart_overhead

        # Slack relative to finishing entirely on on-demand with a single restart overhead.
        slack = time_left - (remaining_work + R)

        # Decide if we must commit to on-demand to safely finish.
        if not self._committed_to_on_demand and slack <= self._commit_buffer:
            self._committed_to_on_demand = True

        if self._committed_to_on_demand:
            # From now on, always use on-demand.
            return ClusterType.ON_DEMAND

        # Pre-commit phase: we trade cost vs remaining slack.

        if has_spot:
            # Spot available and we still have reasonable slack: use spot.
            return ClusterType.SPOT

        # Spot unavailable in current region.
        # If we still have plenty of slack, it is safe to idle and wait.
        if slack > self._idle_slack_threshold:
            return ClusterType.NONE

        # Slack is no longer large; use on-demand to maintain progress.
        return ClusterType.ON_DEMAND