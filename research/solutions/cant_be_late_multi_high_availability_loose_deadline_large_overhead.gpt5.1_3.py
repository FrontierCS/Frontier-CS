import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy focusing on Spot with safe On-Demand fallback."""

    NAME = "my_strategy"

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

        # Internal state for efficient progress tracking
        self._acc_work_seconds = 0.0
        self._last_task_segments_len = 0

        # Flag indicating we've switched to guaranteed-completion mode on On-Demand
        self._committed_to_ondemand = False

        # Cache scalar versions of core parameters (defensive against list/tuple forms)
        td = getattr(self, "task_duration", 0.0)
        if isinstance(td, (list, tuple)):
            self._task_duration_seconds = float(sum(td))
        else:
            self._task_duration_seconds = float(td)

        dl = getattr(self, "deadline", 0.0)
        if isinstance(dl, (list, tuple)):
            self._deadline_seconds = float(sum(dl))
        else:
            self._deadline_seconds = float(dl)

        ro = getattr(self, "restart_overhead", 0.0)
        if isinstance(ro, (list, tuple)):
            self._restart_overhead_seconds = float(sum(ro))
        else:
            self._restart_overhead_seconds = float(ro)

        # Will be set on first _step when env is available
        self._gap_seconds = None

        return self

    def _update_progress_cache(self) -> None:
        """Incrementally track total work done without re-summing the full list."""
        current_len = len(self.task_done_time)
        if current_len > self._last_task_segments_len:
            new_segments = self.task_done_time[self._last_task_segments_len : current_len]
            # Usually one element; incremental sum keeps this O(1) amortized
            self._acc_work_seconds += sum(new_segments)
            self._last_task_segments_len = current_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize gap_seconds once env becomes available
        if self._gap_seconds is None:
            self._gap_seconds = float(self.env.gap_seconds)

        # Update cached progress
        self._update_progress_cache()

        remaining_work = self._task_duration_seconds - self._acc_work_seconds
        if remaining_work <= 0.0:
            # Task already complete; no need to run further
            return ClusterType.NONE

        # If already in fail-safe On-Demand mode, keep using it until completion
        if self._committed_to_ondemand:
            return ClusterType.ON_DEMAND

        time_now = float(self.env.elapsed_seconds)
        slack = self._deadline_seconds - time_now

        # If already at/past deadline, best effort: switch to On-Demand
        if slack <= 0.0:
            self._committed_to_ondemand = True
            return ClusterType.ON_DEMAND

        # Time required to complete if we start/continue on On-Demand **now**,
        # conservatively assuming a fresh restart overhead from this moment.
        required_time_if_ondemand_now = self._restart_overhead_seconds + remaining_work

        # Determine if it's safe to spend one more step without committing to On-Demand,
        # assuming worst-case zero progress during that step.
        safe_to_wait_one_step = required_time_if_ondemand_now <= (slack - self._gap_seconds)

        # If it's not safe to wait, immediately switch to On-Demand and stay there.
        if not safe_to_wait_one_step:
            self._committed_to_ondemand = True
            return ClusterType.ON_DEMAND

        # Safe region: Prefer Spot for low cost when available.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable but still enough slack; wait without incurring cost.
        return ClusterType.NONE