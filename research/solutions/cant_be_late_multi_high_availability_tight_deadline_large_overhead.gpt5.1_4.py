import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

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

        # Initialize internal state
        self.lock_to_od = False
        self._progress_sum = 0.0
        self._last_td_len = 0

        # Extract scalar versions of key parameters (in seconds)
        self._task_duration_scalar = self._extract_scalar_attr("task_duration")
        self._deadline_scalar = self._extract_scalar_attr("deadline")
        self._restart_overhead_scalar = self._extract_scalar_attr("restart_overhead")

        base_slack = max(0.0, self._deadline_scalar - self._task_duration_scalar)
        self._initial_slack = base_slack

        if base_slack <= 0.0:
            commit_slack = 0.0
        else:
            # Base commit slack: 25% of initial slack, capped at 3 hours
            commit_slack = 0.25 * base_slack
            max_commit = 3.0 * 3600.0
            if commit_slack > max_commit:
                commit_slack = max_commit
            # Ensure room for multiple restart overheads
            min_commit = 4.0 * self._restart_overhead_scalar
            if commit_slack < min_commit:
                commit_slack = min_commit
            # Don't exceed actual initial slack
            if commit_slack > base_slack:
                commit_slack = base_slack

        self.commit_slack = commit_slack

        return self

    def _extract_scalar_attr(self, name: str) -> float:
        """Helper to robustly extract scalar seconds value from strategy attributes."""
        val = getattr(self, name, 0.0)
        if isinstance(val, (list, tuple)):
            if val:
                val = val[0]
            else:
                val = 0.0
        try:
            return float(val)
        except Exception:
            # Fallbacks if something unexpected happens
            if name == "task_duration" and hasattr(self, "task_duration_hours"):
                hrs = getattr(self, "task_duration_hours", [0.0])
                if isinstance(hrs, (list, tuple)) and hrs:
                    return float(hrs[0]) * 3600.0
                return float(hrs) * 3600.0
            if name == "deadline" and hasattr(self, "deadline_hours"):
                return float(getattr(self, "deadline_hours", 0.0)) * 3600.0
            if name == "restart_overhead" and hasattr(self, "restart_overhead_hours"):
                hrs = getattr(self, "restart_overhead_hours", [0.0])
                if isinstance(hrs, (list, tuple)) and hrs:
                    return float(hrs[0]) * 3600.0
                return float(hrs) * 3600.0
            return 0.0

    def _update_progress_sum(self) -> None:
        """Incrementally track total completed work time."""
        td = self.task_done_time
        current_len = len(td)
        if current_len > self._last_td_len:
            s = 0.0
            for v in td[self._last_td_len:]:
                s += v
            self._progress_sum += s
            self._last_td_len = current_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Defensive initialization (in case solve wasn't called for some reason)
        if not hasattr(self, "_progress_sum"):
            self._progress_sum = 0.0
            self._last_td_len = 0
        if not hasattr(self, "_task_duration_scalar"):
            self._task_duration_scalar = self._extract_scalar_attr("task_duration")
        if not hasattr(self, "_deadline_scalar"):
            self._deadline_scalar = self._extract_scalar_attr("deadline")
        if not hasattr(self, "_restart_overhead_scalar"):
            self._restart_overhead_scalar = self._extract_scalar_attr("restart_overhead")
        if not hasattr(self, "lock_to_od"):
            self.lock_to_od = False
        if not hasattr(self, "commit_slack"):
            # Conservative default if not set in solve
            self.commit_slack = 4.0 * self._restart_overhead_scalar

        # Update progress tracking
        self._update_progress_sum()

        work_remaining = self._task_duration_scalar - self._progress_sum
        if work_remaining <= 0.0:
            # Task already complete; no need to run more
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_remaining = self._deadline_scalar - elapsed

        # Slack ignoring future overhead
        slack = time_remaining - work_remaining

        # Account for currently pending restart overhead as "extra work"
        remaining_overhead = getattr(self, "remaining_restart_overhead", 0.0)
        effective_slack = slack - remaining_overhead

        # If we're running out of slack, permanently switch to on-demand
        if (not self.lock_to_od) and (effective_slack <= self.commit_slack or effective_slack <= 0.0):
            self.lock_to_od = True

        if self.lock_to_od:
            return ClusterType.ON_DEMAND

        # Opportunistic spot usage while we still have comfortable slack
        if has_spot:
            return ClusterType.SPOT

        # Fallback to on-demand when spot is unavailable
        return ClusterType.ON_DEMAND