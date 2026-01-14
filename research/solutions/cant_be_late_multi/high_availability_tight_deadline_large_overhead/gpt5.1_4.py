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

        # Initialize internal state (in seconds)
        td = getattr(self, "task_duration", 0.0)
        if isinstance(td, (list, tuple)):
            self._task_duration = float(td[0])
        else:
            self._task_duration = float(td)

        ro = getattr(self, "restart_overhead", 0.0)
        if isinstance(ro, (list, tuple)):
            self._restart_overhead = float(ro[0])
        else:
            self._restart_overhead = float(ro)

        self._deadline = float(self.deadline)
        self._gap = float(self.env.gap_seconds)

        self._last_task_done_len = len(getattr(self, "task_done_time", []))
        if self._last_task_done_len > 0:
            self._progress = float(sum(self.task_done_time))
        else:
            self._progress = 0.0

        self._committed_od = False
        self._internal_inited = True

        return self

    def _update_progress(self) -> None:
        """Incrementally update cached progress from task_done_time list."""
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return
        current_len = len(tdt)
        last_len = getattr(self, "_last_task_done_len", 0)
        if current_len > last_len:
            # Sum only new segments since last step.
            new_segments = tdt[last_len:current_len]
            self._progress += float(sum(new_segments))
            self._last_task_done_len = current_len

    def _safe_to_wait_one_step(self, remaining: float, now: float) -> bool:
        """
        Check if we can afford to potentially make zero progress during the
        upcoming step and still be able to finish on time by switching to
        on-demand afterwards.
        """
        # Time left after taking one more step.
        time_after_step = self._deadline - (now + self._gap)
        if time_after_step <= 0.0:
            return False

        # Max possible work we can do on on-demand, starting after this step,
        # accounting for a single restart overhead.
        capacity_after_step = time_after_step - self._restart_overhead
        if capacity_after_step < 0.0:
            capacity_after_step = 0.0

        # Safe if remaining work fits completely in this capacity.
        return remaining <= capacity_after_step + 1e-9

    def _lazy_init_if_needed(self):
        """Best-effort lazy initialization if solve() was not called."""
        if getattr(self, "_internal_inited", False):
            return

        td = getattr(self, "task_duration", 0.0)
        if isinstance(td, (list, tuple)):
            self._task_duration = float(td[0])
        else:
            self._task_duration = float(td or 0.0)

        ro = getattr(self, "restart_overhead", 0.0)
        if isinstance(ro, (list, tuple)):
            self._restart_overhead = float(ro[0])
        else:
            self._restart_overhead = float(ro or 0.0)

        self._deadline = float(getattr(self, "deadline", 0.0))

        env = getattr(self, "env", None)
        if env is not None and hasattr(env, "gap_seconds"):
            self._gap = float(env.gap_seconds)
        else:
            self._gap = 1.0

        tdt = getattr(self, "task_done_time", [])
        self._last_task_done_len = len(tdt)
        self._progress = float(sum(tdt)) if self._last_task_done_len > 0 else 0.0

        self._committed_od = False
        self._internal_inited = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Ensure state is initialized.
        self._lazy_init_if_needed()

        # Update accumulated progress.
        self._update_progress()

        remaining = self._task_duration - self._progress
        if remaining <= 1e-9:
            # Task completed; no need to run more.
            return ClusterType.NONE

        now = self.env.elapsed_seconds
        time_left = self._deadline - now

        # If already committed to on-demand, keep using it to avoid any
        # further restart overheads or uncertainty.
        if self._committed_od:
            return ClusterType.ON_DEMAND

        if time_left <= 0.0:
            # Out of time; try on-demand anyway (can't fix deadline miss).
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # Check if it's safe to risk one more step with potential zero progress.
        if not self._safe_to_wait_one_step(remaining, now):
            # Must commit to on-demand now to guarantee completion.
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # Still safe to wait; favor cheap spot, otherwise pause.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE