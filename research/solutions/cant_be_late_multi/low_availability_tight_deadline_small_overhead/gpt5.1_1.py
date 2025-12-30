import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with deadline safety."""

    NAME = "cant_be_late_multi_region_v1"

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

        # Internal tracking of accumulated work to avoid O(n) sums each step.
        self._initialized = False
        self._done_work = 0.0
        self._last_task_segments = 0

        return self

    def _ensure_initialized(self) -> None:
        """Lazy initialization based on current environment state."""
        if self._initialized:
            return

        try:
            segments = self.task_done_time
        except AttributeError:
            # In case env has not attached task_done_time yet.
            self._done_work = 0.0
            self._last_task_segments = 0
            self._initialized = True
            return

        if segments:
            self._done_work = float(sum(segments))
            self._last_task_segments = len(segments)
        else:
            self._done_work = 0.0
            self._last_task_segments = 0

        self._initialized = True

    def _update_done_work(self) -> None:
        """Incrementally update total completed work based on new segments."""
        segments = self.task_done_time
        curr_len = len(segments)
        if curr_len > self._last_task_segments:
            new_work = 0.0
            for v in segments[self._last_task_segments:]:
                new_work += float(v)
            self._done_work += new_work
            self._last_task_segments = curr_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        self._ensure_initialized()
        self._update_done_work()

        # Remaining required work in seconds.
        remaining_work = self.task_duration - self._done_work
        if remaining_work <= 0.0:
            # Job finished; no need to run more.
            return ClusterType.NONE

        # Remaining wall-clock time until deadline in seconds.
        time_elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - time_elapsed

        if time_remaining <= 0.0:
            # Already past deadline; keep using on-demand (penalty is already incurred).
            return ClusterType.ON_DEMAND

        gap = self.env.gap_seconds
        restart_overhead = self.restart_overhead

        # Conservative "one more gamble" budget:
        #   - We might waste the next full step (gap) with no useful work.
        #   - We may incur up to two restart overheads (existing + new).
        #   - Then we must be able to finish all remaining work on on-demand.
        worst_case_time_needed = remaining_work + 2.0 * restart_overhead + gap

        # If we no longer have enough slack to afford that worst case,
        # immediately switch to on-demand and stick with it.
        if worst_case_time_needed >= time_remaining:
            return ClusterType.ON_DEMAND

        # Still have comfortable slack: prefer cheap spot when available.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable and far from deadline: wait to avoid expensive on-demand usage.
        return ClusterType.NONE