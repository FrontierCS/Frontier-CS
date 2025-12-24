import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cant_be_late_safe_spot_hedging"

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

        # These will be fully initialized once env is attached (in _step).
        self._initialized_runtime = False
        self.work_done_so_far = 0.0
        self._last_task_segments_len = 0
        self.committed_to_od = False
        return self

    def _initialize_runtime_state(self) -> None:
        """Lazy initialization once the environment is available."""
        # Time step size
        self.gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if self.gap <= 0.0:
            # Fallback to avoid division by zero; value doesn't matter much for logic.
            self.gap = 60.0

        # Ensure scalar floats for key parameters
        self.task_duration = float(self.task_duration)
        self.deadline = float(self.deadline)
        self.restart_overhead = float(self.restart_overhead)

        # Initialize work tracking from any existing segments
        if self.task_done_time:
            self.work_done_so_far = float(sum(self.task_done_time))
            self._last_task_segments_len = len(self.task_done_time)
        else:
            self.work_done_so_far = 0.0
            self._last_task_segments_len = 0

        self.committed_to_od = False
        self._initialized_runtime = True

    def _update_work_done(self) -> None:
        """Incrementally update total work done to avoid O(n) summation each step."""
        segments = self.task_done_time
        current_len = len(segments)
        if current_len > self._last_task_segments_len:
            new_work = 0.0
            for i in range(self._last_task_segments_len, current_len):
                new_work += segments[i]
            self.work_done_so_far += new_work
            self._last_task_segments_len = current_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        if not getattr(self, "_initialized_runtime", False):
            self._initialize_runtime_state()

        # Update accumulated work
        self._update_work_done()

        # Remaining work and time
        remaining_work = self.task_duration - self.work_done_so_far
        if remaining_work <= 0.0:
            # Task already completed; avoid incurring any further cost.
            return ClusterType.NONE

        elapsed = float(self.env.elapsed_seconds)
        time_left = self.deadline - elapsed

        if time_left <= 0.0:
            # Past deadline but task not done: always use fastest reliable option.
            self.committed_to_od = True
            return ClusterType.ON_DEMAND

        # Estimate worst-case restart overhead if we switch to a fresh cluster now.
        pending_overhead = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        # Be conservative: we might have to pay up to the larger of standard or pending overhead.
        overhead_future = max(self.restart_overhead, pending_overhead)

        # Safety margin: accounts for discretization, overhead modeling error, and some buffer.
        margin = max(2.0 * self.gap, 5.0 * self.restart_overhead)

        if not self.committed_to_od:
            # Minimal wall-clock time needed if we immediately switch to on-demand
            # and then run without interruption.
            min_time_needed_if_od_now = remaining_work + overhead_future

            # If staying in speculative mode (spot/idle) any longer might risk missing
            # the deadline even with pure on-demand from this point, permanently
            # commit to on-demand.
            if time_left <= min_time_needed_if_od_now + margin:
                self.committed_to_od = True

        if self.committed_to_od:
            # Hard commitment to on-demand to guarantee completion.
            return ClusterType.ON_DEMAND

        # Speculative phase: prefer Spot whenever available.
        if has_spot:
            return ClusterType.SPOT

        # No Spot available; wait to preserve slack for potential future Spot.
        return ClusterType.NONE
