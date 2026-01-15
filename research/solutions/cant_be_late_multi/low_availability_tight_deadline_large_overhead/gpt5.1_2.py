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

        self._initialize_internal_state()
        return self

    def _initialize_internal_state(self):
        # Internal state for tracking progress and policy mode.
        self._committed_to_on_demand = False
        self._work_done = 0.0
        self._last_task_len = 0
        self._last_seen_elapsed = -1.0
        if hasattr(self, "env") and hasattr(self.env, "gap_seconds"):
            self._gap = float(self.env.gap_seconds)
        else:
            self._gap = 1.0

    def _reset_if_new_episode(self):
        # Detect environment reset by a decrease in elapsed time.
        elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        if self._last_seen_elapsed < 0.0:
            # First call ever.
            self._last_seen_elapsed = elapsed
        elif elapsed < self._last_seen_elapsed - 1e-6:
            # New episode detected: reset internal state.
            self._committed_to_on_demand = False
            self._work_done = 0.0
            self._last_task_len = 0
        # Update stored gap each step (in case env changes it).
        if hasattr(self.env, "gap_seconds"):
            self._gap = float(self.env.gap_seconds)
        self._last_seen_elapsed = elapsed

    def _update_work_done(self):
        # Incremental sum of task_done_time to avoid O(N^2).
        segments = self.task_done_time
        n = len(segments)
        if n > self._last_task_len:
            total_new = 0.0
            for i in range(self._last_task_len, n):
                total_new += segments[i]
            self._work_done += total_new
            self._last_task_len = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Handle potential new episode.
        self._reset_if_new_episode()

        # Update internal notion of work done.
        self._update_work_done()

        remaining_work = self.task_duration - self._work_done

        # If task already done, do not run any more clusters.
        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        time_remaining = deadline - elapsed

        # If we've already passed the deadline (should rarely happen), best-effort ON_DEMAND.
        if time_remaining <= 0.0:
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Once we commit to on-demand, we never switch back (avoid further overhead).
        if self._committed_to_on_demand:
            return ClusterType.ON_DEMAND

        gap = self._gap
        restart_overhead = self.restart_overhead

        # Safety check: if waiting one more step (with no progress) would make it
        # impossible to finish using only on-demand before the deadline,
        # then commit to on-demand right now.
        if time_remaining <= remaining_work + restart_overhead + gap:
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Pre-commit phase: maximize cheap Spot usage; otherwise wait.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE