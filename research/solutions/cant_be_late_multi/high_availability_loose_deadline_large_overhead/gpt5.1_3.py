import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with cautious on-demand fallback."""

    NAME = "cant_be_late_heuristic"

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

        # Initialize internal state
        self._committed_to_on_demand = False
        self._progress_done = 0.0
        self._last_task_len = 0

        # Cache scalar parameters (handle possible array/list types defensively)
        self._task_duration_total = self._to_scalar(getattr(self, "task_duration", 0.0))
        self._restart_overhead = self._to_scalar(getattr(self, "restart_overhead", 0.0))
        self._deadline_seconds = self._to_scalar(getattr(self, "deadline", 0.0))

        return self

    @staticmethod
    def _to_scalar(value):
        """Convert value (possibly list/array/scalar) to float scalar."""
        try:
            return float(value)
        except TypeError:
            # Assume indexable container with at least one element
            return float(value[0])

    def _update_progress_cache(self):
        """Incrementally track total completed work to avoid O(n) summations."""
        segments = self.task_done_time
        current_len = len(segments)

        if current_len < self._last_task_len:
            # Environment reset; recompute from scratch
            total = 0.0
            for v in segments:
                total += v
            self._progress_done = total
            self._last_task_len = current_len
            return

        if current_len > self._last_task_len:
            total_add = 0.0
            for i in range(self._last_task_len, current_len):
                total_add += segments[i]
            self._progress_done += total_add
            self._last_task_len = current_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update cached progress
        self._update_progress_cache()

        remaining_work = self._task_duration_total - self._progress_done
        if remaining_work <= 0.0:
            # Task completed: no need to run further
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        if elapsed >= self._deadline_seconds:
            # Already at or beyond deadline; just use on-demand to minimize further delay
            return ClusterType.ON_DEMAND

        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0

        # Decide if we must commit to on-demand to safely meet deadline
        if not self._committed_to_on_demand:
            # Conservative latest-commit rule:
            # If waiting one more step without progress would push the
            # earliest possible on-demand completion past the deadline,
            # commit to on-demand now.
            if elapsed + remaining_work + self._restart_overhead + gap >= self._deadline_seconds:
                self._committed_to_on_demand = True

        if self._committed_to_on_demand:
            return ClusterType.ON_DEMAND

        # Pre-commit phase: use Spot when available, otherwise wait.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable and we still have slack: wait to avoid on-demand cost.
        return ClusterType.NONE