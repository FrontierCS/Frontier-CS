import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with deadline guarantee."""

    NAME = "cant_be_late_multi_region_simple"

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

        # Total task duration and deadline are provided by base class in seconds.
        self.initial_slack = max(0.0, float(self.deadline - self.task_duration))

        # Efficient tracking of completed work time to avoid O(n^2) sum operations.
        self._accumulated_done_time = 0.0
        self._last_task_segments = 0

        # Control flags and parameters (filled later when env is available).
        self._committed_to_od = False
        self._internal_initialized = False

        return self

    def _initialize_internal(self) -> None:
        """Initialize parameters that depend on the environment."""
        self._internal_initialized = True

        # Gap between decisions (seconds).
        self.gap_seconds = float(getattr(self.env, "gap_seconds", 0.0))

        # Restart overhead (seconds).
        self.restart_overhead = float(self.restart_overhead)

        # Slack threshold (seconds) for switching permanently to on-demand.
        # Heuristic: at least covers several overheads + a couple of gaps,
        # but no more than a fraction of the initial slack.
        safe_min_margin = 2.0 * self.restart_overhead + 2.0 * self.gap_seconds
        base_threshold = 0.25 * self.initial_slack

        if self.initial_slack <= 0.0:
            # No slack: use conservative margin.
            self.slack_threshold = safe_min_margin
        else:
            max_threshold = 0.8 * self.initial_slack
            thr = max(safe_min_margin, base_threshold)
            if max_threshold > 0.0 and thr > max_threshold:
                thr = max_threshold
            if thr > self.initial_slack:
                thr = 0.9 * self.initial_slack
            self.slack_threshold = thr

    def _update_done_time(self) -> None:
        """Incrementally update total successful work time."""
        cur_len = len(self.task_done_time)
        if cur_len > self._last_task_segments:
            added = 0.0
            for i in range(self._last_task_segments, cur_len):
                added += self.task_done_time[i]
            self._accumulated_done_time += added
            self._last_task_segments = cur_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        if not self._internal_initialized:
            self._initialize_internal()

        # Update cumulative completed work.
        self._update_done_time()

        remaining_work = self.task_duration - self._accumulated_done_time
        if remaining_work <= 0.0:
            # Task is already complete; avoid incurring any additional cost.
            return ClusterType.NONE

        elapsed = float(self.env.elapsed_seconds)
        time_left = self.deadline - elapsed

        if time_left <= 0.0:
            # Past the deadline but task not marked done yet; run OD to minimize extra delay.
            return ClusterType.ON_DEMAND

        # Slack time ignoring any future overheads.
        slack = time_left - remaining_work

        # Pending overhead from the last restart, if any.
        pending_overhead = float(getattr(self, "remaining_restart_overhead", 0.0))

        if not self._committed_to_od:
            # Condition 1: Slack falls below heuristic threshold.
            commit = slack <= self.slack_threshold

            # Condition 2: Conservative check—ensure that even in a bad case
            # (one more interruption plus committing to OD) we can still finish.
            conservative_time_needed = (
                remaining_work
                + pending_overhead
                + 2.0 * self.restart_overhead
                + self.gap_seconds
            )
            if time_left <= conservative_time_needed:
                commit = True

            # Condition 3: Absolute safety—if time_left is already close to remaining_work.
            if time_left <= remaining_work:
                commit = True

            if commit:
                self._committed_to_od = True

        if self._committed_to_od:
            # From this point on we exclusively use On-Demand to guarantee completion.
            return ClusterType.ON_DEMAND

        # Speculative phase: prefer cheap Spot when available; otherwise wait.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE
