import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy implementation."""

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

        # Internal state for tracking work done efficiently.
        self._work_done = 0.0
        self._td_len = 0
        self._committed_to_od = False
        self._run_initialized = False

        return self

    # Internal helpers -----------------------------------------------------

    def _reset_run_state(self):
        """Reset per-run state, called when env is (re)initialized."""
        td = getattr(self, "task_done_time", [])
        self._td_len = len(td)
        self._work_done = float(sum(td)) if td else 0.0
        self._committed_to_od = False
        self._run_initialized = True

    def _update_work_done(self):
        """Incrementally update total work done from task_done_time list."""
        td = self.task_done_time
        cur_len = len(td)
        if cur_len > self._td_len:
            # Sum only the new segments.
            self._work_done += float(sum(td[self._td_len:cur_len]))
            self._td_len = cur_len

    # Core decision logic --------------------------------------------------

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Detect new run by elapsed_seconds == 0 or first call.
        if not getattr(self, "_run_initialized", False) or self.env.elapsed_seconds == 0:
            self._reset_run_state()
        else:
            self._update_work_done()

        # If task already completed, no need to run more.
        remaining_work = max(0.0, float(self.task_duration) - self._work_done)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Time-related parameters.
        elapsed = float(self.env.elapsed_seconds)
        deadline = float(self.deadline)
        time_left = deadline - elapsed
        if time_left <= 0.0:
            # Already at/past deadline; try OD to minimize penalty (environment handles failure).
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        gap = float(getattr(self.env, "gap_seconds", 1.0))

        # Restart overhead: ensure scalar.
        ro = self.restart_overhead
        try:
            overhead = float(ro)
        except TypeError:
            # Fallback if restart_overhead is a sequence.
            overhead = float(ro[0])

        # Minimal additional time to finish if we switch to OD now and run only OD.
        minimal_od_time = remaining_work + overhead

        # Slack time = how much we can afford to waste and still finish with OD.
        slack = time_left - minimal_od_time

        # Safety margin before committing to OD.
        # Use a couple of overheads or steps as buffer.
        margin = 2.0 * max(gap, overhead)

        # If we've already decided to stick with OD, always return OD.
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # If we don't even have enough time for OD fallback, or we're too close, commit to OD.
        if slack <= 0.0 or slack <= margin:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # We have comfortable slack: prefer SPOT when available.
        if has_spot:
            return ClusterType.SPOT

        # SPOT not available: decide between waiting (NONE) and switching to OD.
        # Check if we can safely idle for one gap and still have sufficient slack for OD + margin.
        time_left_after_idle = time_left - gap
        if time_left_after_idle <= 0.0:
            # Can't afford to idle at all.
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        slack_after_idle = time_left_after_idle - minimal_od_time
        if slack_after_idle >= margin:
            # Still plenty of slack even after idling one step: wait for cheaper SPOT.
            return ClusterType.NONE

        # Not safe to keep waiting: commit to OD.
        self._committed_to_od = True
        return ClusterType.ON_DEMAND
