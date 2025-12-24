import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with spot-first, safe on-demand fallback."""

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

        # Cached total work done so far (seconds)
        self._cached_segments_len = 0
        self._cached_work_done = 0.0

        # Whether we've permanently committed to on-demand
        self._committed_to_od = False

        # Safe buffer time for switching to on-demand (seconds), initialized lazily
        self._safe_od_buffer = None

        return self

    def _update_work_done_cache(self) -> None:
        """Incrementally maintain total work done from task_done_time segments."""
        segments = self.task_done_time
        cur_len = len(segments)
        if cur_len > self._cached_segments_len:
            total_new = 0.0
            for i in range(self._cached_segments_len, cur_len):
                total_new += segments[i]
            self._cached_work_done += total_new
            self._cached_segments_len = cur_len

    def _ensure_safe_buffer(self) -> None:
        """Initialize the safe on-demand buffer if not set."""
        if self._safe_od_buffer is None:
            gap = getattr(self.env, "gap_seconds", 1.0)
            # Require enough slack for one full restart_overhead plus a couple of gaps
            self._safe_od_buffer = self.restart_overhead + 2.0 * gap

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update cached work done and buffer
        self._update_work_done_cache()
        self._ensure_safe_buffer()

        # Remaining work and time (seconds)
        remaining_work = self.task_duration - self._cached_work_done
        if remaining_work <= 0.0:
            # Task finished: do not run any more instances
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed

        if remaining_time <= 0.0:
            # Already at/past deadline but not done; just use on-demand
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # If we've already committed, stay on on-demand to guarantee completion
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Decide whether we must now commit to on-demand to safely meet deadline
        # Safe commit condition: even if we start a fresh on-demand instance now
        # and pay one full restart_overhead, we can still finish by deadline.
        # We add a small discrete-time safety buffer (self._safe_od_buffer).
        if remaining_time <= remaining_work + self._safe_od_buffer:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, still safely in the spot-favorable region.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable and we still have slack: wait (no cluster) to save cost.
        return ClusterType.NONE
