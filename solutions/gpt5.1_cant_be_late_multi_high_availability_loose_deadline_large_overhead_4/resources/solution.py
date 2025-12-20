import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy focused on meeting deadlines with low cost."""

    NAME = "cant_be_late_v1"

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

        # Internal state for efficient progress tracking and control.
        self._committed_to_on_demand = False
        self._accumulated_work = 0.0
        self._last_task_done_idx = 0

        return self

    def _update_accumulated_work(self):
        """Incrementally track total work done to avoid O(n) sum each step."""
        td = self.task_done_time
        idx = self._last_task_done_idx
        if idx < len(td):
            new_sum = 0.0
            for v in td[idx:]:
                new_sum += v
            self._accumulated_work += new_sum
            self._last_task_done_idx = len(td)

    def _should_commit_to_on_demand(self, remaining_work: float, time_left: float) -> bool:
        """Determine if we must switch to on-demand to safely meet the deadline."""
        # Estimate one-time restart overhead if we commit now.
        rem_overhead = getattr(self, "remaining_restart_overhead", 0.0)
        commit_overhead = self.restart_overhead
        if rem_overhead > commit_overhead:
            commit_overhead = rem_overhead

        # Time needed with on-demand from now until completion (worst-case).
        commit_needed = remaining_work + commit_overhead

        # Safety buffer to account for discretization and modeling mismatch.
        gap = getattr(self.env, "gap_seconds", 0.0)
        if gap < 0.0:
            gap = 0.0
        buffer = commit_overhead + 2.0 * gap

        return time_left <= commit_needed + buffer

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Efficiently update cumulative work done.
        self._update_accumulated_work()

        remaining_work = self.task_duration - self._accumulated_work
        if remaining_work <= 0.0:
            # Task already completed; no need to run further.
            return ClusterType.NONE

        time_elapsed = self.env.elapsed_seconds
        time_left = self.deadline - time_elapsed
        if time_left <= 0.0:
            # Deadline has passed or no time left; running more won't help.
            return ClusterType.NONE

        # Decide whether to commit to on-demand from this point forward.
        if not self._committed_to_on_demand:
            if self._should_commit_to_on_demand(remaining_work, time_left):
                self._committed_to_on_demand = True

        if self._committed_to_on_demand:
            # Once committed, stay on on-demand to avoid further restart overhead
            # and eliminate preemption risk.
            return ClusterType.ON_DEMAND

        # Pre-commit phase: use spot when available, otherwise wait (NONE).
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE
