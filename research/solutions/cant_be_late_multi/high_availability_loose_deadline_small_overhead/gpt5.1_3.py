import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cant_be_late_multi_region_v1"  # REQUIRED: unique identifier

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

        # Internal bookkeeping
        self._last_task_done_len = len(getattr(self, "task_done_time", []))
        self._work_done = float(sum(self.task_done_time)) if self._last_task_done_len > 0 else 0.0
        self.force_on_demand = False

        # Cache scalar task duration and restart overhead in seconds
        td = getattr(self, "task_duration", None)
        if isinstance(td, (list, tuple)):
            self._task_duration = float(td[0]) if td else 0.0
        else:
            self._task_duration = float(td) if td is not None else 0.0

        ro = getattr(self, "restart_overhead", None)
        if isinstance(ro, (list, tuple)):
            self._restart_overhead = float(ro[0]) if ro else 0.0
        else:
            self._restart_overhead = float(ro) if ro is not None else 0.0

        return self

    def _update_work_done(self) -> None:
        """Incrementally track total completed work to avoid O(n) sum each step."""
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return
        current_len = len(segments)
        if current_len > self._last_task_done_len:
            new_segments = segments[self._last_task_done_len:current_len]
            self._work_done += float(sum(new_segments))
            self._last_task_done_len = current_len

    def _get_time_left(self) -> float:
        deadline = getattr(self, "deadline", None)
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        if deadline is None:
            return float("inf")
        return float(deadline - elapsed)

    def _get_gap_seconds(self) -> float:
        return float(getattr(self.env, "gap_seconds", 0.0))

    def _get_remaining_overhead(self) -> float:
        return float(getattr(self, "remaining_restart_overhead", 0.0))

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Update cached total work done
        self._update_work_done()

        remaining_work = max(self._task_duration - self._work_done, 0.0)
        if remaining_work <= 0.0:
            # Task completed; run nothing further.
            return ClusterType.NONE

        # If we've already committed to guaranteed completion via on-demand, stick with it.
        if getattr(self, "force_on_demand", False):
            return ClusterType.ON_DEMAND

        time_left = self._get_time_left()
        gap = self._get_gap_seconds()
        restart_overhead = self._restart_overhead
        remaining_overhead = self._get_remaining_overhead()

        # Conservative upper bound on time needed to finish using only on-demand from now.
        # Includes:
        # - Possible pending restart overhead
        # - New restart overhead for switching to on-demand
        # - Several gap intervals and a constant fudge factor for discretization effects
        safety_margin = 3.0 * gap + 2.0 * restart_overhead + 60.0  # seconds
        time_needed_on_demand = remaining_work + remaining_overhead + restart_overhead + safety_margin

        # If we are close enough to the deadline that we cannot safely wait for spot,
        # switch permanently to on-demand to avoid missing the deadline.
        if time_left <= time_needed_on_demand:
            self.force_on_demand = True
            return ClusterType.ON_DEMAND

        # Cost-minimizing mode with ample slack:
        # - Use Spot whenever available.
        # - If Spot is unavailable, pause to wait for it (no cost) since we still have slack.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE