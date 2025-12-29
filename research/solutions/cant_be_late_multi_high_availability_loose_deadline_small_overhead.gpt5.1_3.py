import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy focusing on deadline safety and low cost."""

    NAME = "cant_be_late_multi_region_v1"

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

        # Caches for fast progress tracking
        self._progress_done = 0.0
        self._last_task_done_index = 0

        # Lazy-init runtime parameters (depend on env)
        self._initialized_runtime = False
        self._bail_margin = 0.0
        self._idle_margin = 0.0
        self._od_min_margin = 0.0

        return self

    def _lazy_init_runtime(self) -> None:
        """Initialize runtime-dependent thresholds once env is available."""
        if self._initialized_runtime:
            return

        gap = float(self.env.gap_seconds)
        overhead = float(self.restart_overhead)

        # Minimum margin (time slack) needed to safely finish using only On-Demand
        # from the decision point onward, accounting for one restart overhead and
        # one step granularity.
        self._od_min_margin = gap + overhead

        # Bail margin: if margin <= this, we must stick to On-Demand only.
        # Chosen conservatively so that even after a worst-case bad Spot step
        # (losing up to gap + overhead of margin), we would still have at least
        # _od_min_margin remaining when we switch to On-Demand.
        unit = gap + overhead
        self._bail_margin = 2.0 * unit

        # Idle margin: when Spot is unavailable and margin > _idle_margin,
        # it is safe and cost-effective to wait (ClusterType.NONE). Once the
        # margin drops below this, we start using On-Demand if Spot is absent.
        self._idle_margin = self._bail_margin + gap

        self._initialized_runtime = True

    def _update_progress_cache(self) -> None:
        """Incrementally track total work done to avoid O(N) sum each step."""
        td = self.task_done_time
        if td is None:
            return
        n = len(td)
        if n > self._last_task_done_index:
            # Sum only the new segments appended since last step.
            new_sum = 0.0
            for v in td[self._last_task_done_index : n]:
                new_sum += v
            self._progress_done += new_sum
            self._last_task_done_index = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """Decide next action based on current state."""
        # Ensure runtime thresholds are initialized
        self._lazy_init_runtime()

        # Update cached total progress
        self._update_progress_cache()

        # Remaining work (seconds)
        remaining_work = self.task_duration - self._progress_done
        if remaining_work <= 0:
            # Task already completed
            return ClusterType.NONE

        # Remaining wall-clock time until deadline (seconds)
        remaining_time = self.deadline - self.env.elapsed_seconds

        # If already past deadline, nothing we do can avoid the penalty, but we
        # still return a valid action (cheap choice: Spot if available).
        if remaining_time <= 0:
            return ClusterType.SPOT if has_spot else ClusterType.NONE

        # Margin: extra time beyond required work
        margin = remaining_time - remaining_work

        # If margin is small (or negative), we must rely on On-Demand only to
        # avoid any further risk from Spot interruptions or idle waiting.
        if margin <= self._bail_margin:
            return ClusterType.ON_DEMAND

        # We have comfortable slack here.
        if has_spot:
            # Use Spot whenever available and we are not in the bailout zone.
            return ClusterType.SPOT

        # Spot unavailable in this timestep.
        # If slack is large enough, wait (NONE) to avoid expensive On-Demand.
        if margin > self._idle_margin:
            return ClusterType.NONE

        # Slack is moderate: cannot afford to keep waiting, so use On-Demand.
        return ClusterType.ON_DEMAND