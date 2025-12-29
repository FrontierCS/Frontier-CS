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

        # Internal state for efficient progress tracking and control
        self._committed_ondemand = False
        self._work_done_cache = 0.0
        self._task_done_len_cache = 0

        # Cache scalar task duration / deadline / overhead in seconds
        td = getattr(self, "task_duration", None)
        if isinstance(td, (list, tuple)):
            self._task_total = float(td[0])
        else:
            self._task_total = float(td) if td is not None else float(config["duration"]) * 3600.0

        dl = getattr(self, "deadline", None)
        self._deadline_seconds = float(dl) if dl is not None else float(config["deadline"]) * 3600.0

        ro = getattr(self, "restart_overhead", None)
        self._restart_overhead_seconds = float(ro) if ro is not None else float(config["overhead"]) * 3600.0

        return self

    def _update_work_done_cache(self) -> None:
        """Incrementally maintain total completed work time."""
        lst = getattr(self, "task_done_time", None)
        if not lst:
            return
        n = len(lst)
        if n > self._task_done_len_cache:
            delta = 0.0
            for i in range(self._task_done_len_cache, n):
                delta += lst[i]
            self._work_done_cache += delta
            self._task_done_len_cache = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Ensure internal state is initialized even if solve() was bypassed
        if not hasattr(self, "_committed_ondemand"):
            self._committed_ondemand = False
            self._work_done_cache = 0.0
            self._task_done_len_cache = 0
            td = getattr(self, "task_duration", None)
            if isinstance(td, (list, tuple)):
                self._task_total = float(td[0])
            else:
                self._task_total = float(td) if td is not None else 0.0
            dl = getattr(self, "deadline", None)
            self._deadline_seconds = float(dl) if dl is not None else 0.0
            ro = getattr(self, "restart_overhead", None)
            self._restart_overhead_seconds = float(ro) if ro is not None else 0.0

        # Update accumulated work done efficiently
        self._update_work_done_cache()
        work_done = self._work_done_cache
        remaining_work = self._task_total - work_done
        if remaining_work <= 0.0:
            # Task completed; no need to run more
            return ClusterType.NONE

        # Once committed to on-demand, always stay on on-demand
        if self._committed_ondemand:
            return ClusterType.ON_DEMAND

        # Time bookkeeping
        elapsed = self.env.elapsed_seconds
        deadline = self._deadline_seconds
        time_left = deadline - elapsed
        if time_left <= 0.0:
            # Already at/after deadline; best we can do is run on-demand
            self._committed_ondemand = True
            return ClusterType.ON_DEMAND

        gap = self.env.gap_seconds
        overhead = self._restart_overhead_seconds

        # If even switching to on-demand now cannot finish, still choose ON_DEMAND
        # (environment will apply penalty for missing deadline).
        if time_left <= remaining_work + overhead:
            self._committed_ondemand = True
            return ClusterType.ON_DEMAND

        # Safety condition: can we afford to spend the next step without guaranteed progress
        # (i.e., a completely wasted step) and still finish by deadline using on-demand?
        # Worst case for the next step: 0 useful work, then we switch to ON_DEMAND and pay
        # up to 'overhead' restart delay.
        # Require: time_left - gap >= remaining_work + overhead
        # => time_left >= remaining_work + overhead + gap
        if time_left < remaining_work + overhead + gap:
            # Must commit to on-demand now to safely finish
            self._committed_ondemand = True
            return ClusterType.ON_DEMAND

        # Safe to continue gambling on spot or waiting.
        if has_spot:
            return ClusterType.SPOT

        # No spot right now; wait to preserve slack and potential future spot usage.
        return ClusterType.NONE