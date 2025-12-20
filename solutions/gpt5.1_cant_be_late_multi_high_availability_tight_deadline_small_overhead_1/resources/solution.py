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
            trace_files=config.get("trace_files", []),
        )
        super().__init__(args)

        # Internal state for tracking progress efficiently.
        self._strategy_initialized = False
        return self

    def _initialize_internal_state(self):
        """Lazily initialize internal state needed for the strategy."""
        if self._strategy_initialized:
            return
        self._strategy_initialized = True

        # Determine the correct enum member for "no cluster".
        none_attr = None
        if hasattr(ClusterType, "NONE"):
            none_attr = ClusterType.NONE
        elif hasattr(ClusterType, "None"):
            none_attr = getattr(ClusterType, "None")
        else:
            # Fallback: take the first enum member (should rarely be needed).
            try:
                none_attr = list(ClusterType)[0]
            except Exception:
                none_attr = None
        self._none_cluster_type = none_attr

        # Once we commit to on-demand, we never go back to spot.
        self._force_on_demand = False

        # Track cumulative work done without recomputing sum(task_done_time)
        # on every step (which would be O(n^2)).
        segments = getattr(self, "task_done_time", [])
        self._last_task_segments_len = len(segments)
        self._work_done = float(sum(segments)) if segments else 0.0

    def _update_work_done(self):
        """Update cached total work done using new task_done_time segments."""
        segments = self.task_done_time
        current_len = len(segments)
        if current_len > self._last_task_segments_len:
            new_segments = segments[self._last_task_segments_len:current_len]
            if new_segments:
                self._work_done += float(sum(new_segments))
            self._last_task_segments_len = current_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Ensure internal fields are ready.
        self._initialize_internal_state()
        self._update_work_done()

        # Basic quantities (in seconds).
        gap = self.env.gap_seconds
        t = self.env.elapsed_seconds
        time_left = self.deadline - t
        remaining_work = max(self.task_duration - self._work_done, 0.0)
        overhead = self.restart_overhead

        # If task is already complete, don't run anything.
        if remaining_work <= 0.0:
            return (
                self._none_cluster_type
                if self._none_cluster_type is not None
                else ClusterType.ON_DEMAND
            )

        # If we've already decided to stick with on-demand, do so.
        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        # If there is effectively no time left, we can only try on-demand.
        if time_left <= 0.0:
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        # If even immediate on-demand can't finish in time, still choose it
        # (we've already missed the deadline, but this is best effort).
        if time_left <= remaining_work + overhead:
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        # Decide whether we can safely risk one more step with zero progress
        # (e.g., due to spot unavailability or preemption).
        #
        # After waiting one more step (gap seconds) with zero progress, we must
        # still have enough time to finish on pure on-demand:
        #   (time_left - gap) >= remaining_work + overhead
        if time_left - gap >= remaining_work + overhead:
            # Safe to risk this step.
            if has_spot:
                return ClusterType.SPOT
            # No spot: idle to avoid unnecessary cost, since we're still early.
            return (
                self._none_cluster_type
                if self._none_cluster_type is not None
                else ClusterType.ON_DEMAND
            )

        # Not safe to risk losing another gap of time; commit to on-demand.
        self._force_on_demand = True
        return ClusterType.ON_DEMAND
