import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy focused on meeting deadline with minimal cost."""

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

        def _to_scalar(x):
            if isinstance(x, (list, tuple)):
                return float(x[0])
            return float(x)

        # Fallbacks use config (in hours) converted to seconds if attributes missing.
        self._task_duration = _to_scalar(
            getattr(self, "task_duration", float(config["duration"]) * 3600.0)
        )
        self._restart_overhead = _to_scalar(
            getattr(self, "restart_overhead", float(config["overhead"]) * 3600.0)
        )
        self._deadline = _to_scalar(
            getattr(self, "deadline", float(config["deadline"]) * 3600.0)
        )

        # Step size (seconds); default to 1.0 if not present.
        self._gap = getattr(self.env, "gap_seconds", 1.0)

        # Cached progress to avoid O(n) summations every step.
        task_done = getattr(self, "task_done_time", None)
        if task_done is None:
            self.task_done_time = []
            task_done = self.task_done_time

        self._last_task_segments_len = len(task_done)
        total_done = 0.0
        for v in task_done:
            total_done += v
        self._cached_done_time = total_done

        # Once set, we stay on on-demand until completion.
        self._on_demand_only = False

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update cached progress from task_done_time.
        segments = self.task_done_time
        current_len = len(segments)
        if current_len != self._last_task_segments_len:
            if current_len < self._last_task_segments_len:
                # List was reset or changed unexpectedly; recompute from scratch.
                total = 0.0
                for v in segments:
                    total += v
                self._cached_done_time = total
            else:
                # Add only new segments.
                total_new = 0.0
                for i in range(self._last_task_segments_len, current_len):
                    total_new += segments[i]
                self._cached_done_time += total_new
            self._last_task_segments_len = current_len

        # If task is already complete, do not run more.
        if self._cached_done_time >= self._task_duration:
            self._on_demand_only = True
            return ClusterType.NONE

        time_left = self._deadline - self.env.elapsed_seconds
        remaining_work = self._task_duration - self._cached_done_time

        # If not yet locked into on-demand, decide if it's time to switch permanently.
        if (not self._on_demand_only) and (
            time_left <= self._restart_overhead + remaining_work + self._gap
        ):
            self._on_demand_only = True

        if self._on_demand_only:
            # Deterministic, interruption-free completion phase.
            return ClusterType.ON_DEMAND

        # Opportunistic Spot phase: use Spot when available, otherwise wait.
        if has_spot:
            return ClusterType.SPOT
        else:
            # Pause to save cost; safety is guaranteed by the on-demand switch logic above.
            return ClusterType.NONE