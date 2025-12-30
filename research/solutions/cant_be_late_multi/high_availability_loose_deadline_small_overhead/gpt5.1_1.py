import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType

# Handle potential naming differences in ClusterType implementation.
try:
    CLUSTER_NONE = ClusterType.NONE
except AttributeError:  # pragma: no cover
    CLUSTER_NONE = ClusterType.None  # type: ignore[attr-defined]

try:
    CLUSTER_SPOT = ClusterType.SPOT
except AttributeError:  # pragma: no cover
    CLUSTER_SPOT = ClusterType.Spot  # type: ignore[attr-defined]

try:
    CLUSTER_OD = ClusterType.ON_DEMAND
except AttributeError:  # pragma: no cover
    try:
        CLUSTER_OD = ClusterType.ONDEMAND  # type: ignore[attr-defined]
    except AttributeError:
        CLUSTER_OD = ClusterType.OnDemand  # type: ignore[attr-defined]


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy implementation."""

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

        # Internal state for efficient progress tracking.
        self._progress_initialized = False
        self._last_task_len = 0
        self._total_progress = 0.0

        return self

    def _initialize_progress(self) -> None:
        """Lazy initialization of progress-tracking variables."""
        if self._progress_initialized:
            return
        self._progress_initialized = True
        # At first step, task_done_time should correspond to work done so far (likely 0).
        self._last_task_len = len(self.task_done_time)
        if self._last_task_len > 0:
            self._total_progress = float(sum(self.task_done_time))
        else:
            self._total_progress = 0.0

    def _update_progress(self) -> None:
        """Update cached total progress using newly appended segments."""
        # Ensure internal structures are set up.
        if not self._progress_initialized:
            self._initialize_progress()

        n = len(self.task_done_time)
        if n > self._last_task_len:
            # Sum only the new segments since last step.
            added = self.task_done_time[self._last_task_len:n]
            if added:
                self._total_progress += float(sum(added))
            self._last_task_len = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Keep cached progress up to date.
        self._update_progress()

        # Basic parameters (seconds).
        gap = float(getattr(self.env, "gap_seconds", 0.0))
        restart_overhead = float(self.restart_overhead)
        remaining_restart_overhead = float(
            getattr(self, "remaining_restart_overhead", 0.0) or 0.0
        )
        # Effective overhead we must still pay before/while completing on a new cluster.
        effective_overhead = restart_overhead
        if remaining_restart_overhead > effective_overhead:
            effective_overhead = remaining_restart_overhead

        task_duration = float(self.task_duration)

        # Remaining work in seconds.
        remaining_work = task_duration - self._total_progress
        if remaining_work <= 0.0:
            # Task is already complete; no need to run any cluster.
            return CLUSTER_NONE

        now = float(self.env.elapsed_seconds)
        deadline = float(self.deadline)
        time_left = deadline - now

        if time_left <= 0.0:
            # Already at or past deadline; choose ON_DEMAND (penalty is unavoidable anyway).
            return CLUSTER_OD

        # Time needed to finish if we switch to ON_DEMAND now:
        # remaining work + (worst-case pending or new restart overhead).
        od_needed_time = remaining_work + effective_overhead

        # Safety margin based on environment granularity.
        base_unit = max(gap, restart_overhead, 1.0)
        safety = 4.0 * base_unit

        # If even switching to ON_DEMAND now leaves almost no slack,
        # immediately (or continue to) use ON_DEMAND to minimize lateness risk.
        if time_left <= od_needed_time + safety:
            return CLUSTER_OD

        # When Spot is available, decide whether it's still safe to gamble on it.
        if has_spot:
            # Worst-case for taking one more Spot step:
            # - We may waste an entire step of length `gap` with zero progress.
            # - We may incur one restart overhead due to preemption.
            # - Later, when we switch to ON_DEMAND, we may incur another restart overhead.
            # So we require enough extra slack beyond `od_needed_time` to cover
            # approximately `gap + 2 * restart_overhead`, plus safety.
            extra_for_spot_risk = gap + 2.0 * restart_overhead + safety

            if time_left >= od_needed_time + extra_for_spot_risk:
                # Sufficient slack to safely take another Spot step.
                return CLUSTER_SPOT
            # Not enough slack to risk Spot; fall back to guaranteed ON_DEMAND.
            return CLUSTER_OD

        # No Spot available in the current region/time.
        # Decide between idling (NONE) and using expensive ON_DEMAND.

        # If we idle for one step (`gap` seconds) with no progress, then at the next
        # decision point we will have `time_left - gap` remaining and still need
        # `od_needed_time` (since remaining_work unchanged). To keep a margin,
        # require `time_left >= od_needed_time + gap + safety` for idling.
        if time_left >= od_needed_time + gap + safety:
            # Plenty of slack: wait for cheaper Spot instead of paying for OD now.
            return CLUSTER_NONE

        # Slack is getting tight: must use ON_DEMAND to stay on track.
        return CLUSTER_OD