import inspect
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        # Try to call base __init__ with or without args (for compatibility).
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except TypeError:
                pass
        self.args = args

        self._initialized = False
        self._commit_slack = 0.0
        self._committed_to_od = False

        self._completed_work = 0.0
        self._last_task_done_len = 0

    def solve(self, spec_path: str) -> "Solution":
        # Optional: could parse spec_path here; not needed for this heuristic.
        return self

    def _initialize_if_needed(self):
        if self._initialized:
            return

        # Initial slack = time we can afford to not compute (or lose to overheads)
        # and still finish by deadline if we switch to on-demand.
        initial_slack = getattr(self, "deadline", 0.0) - getattr(self, "task_duration", 0.0)
        if initial_slack < 0.0:
            initial_slack = 0.0

        gap = getattr(self.env, "gap_seconds", 60.0)
        overhead = getattr(self, "restart_overhead", 0.0)

        if initial_slack > 0.0:
            # Base commit slack as a fraction of initial slack, but also ensure
            # it is large enough to cover multiple overheads and a few steps.
            base_commit = max(0.1 * initial_slack, 8.0 * overhead, 6.0 * gap)
            # Do not use more than 80% of the total slack for safety.
            commit_slack = min(base_commit, 0.8 * initial_slack)
            # Ensure we always have at least (overhead + 2 * gap) slack when committing,
            # but never require more slack than we actually have.
            min_required = min(initial_slack, overhead + 2.0 * gap)
            if commit_slack < min_required:
                commit_slack = min_required
            self._commit_slack = commit_slack
        else:
            # No slack: must effectively commit immediately.
            self._commit_slack = 0.0

        self._initialized = True

    def _update_completed_work(self):
        """Incrementally track total completed work to avoid repeated full sums."""
        segments = self.task_done_time
        current_len = len(segments)

        if current_len < self._last_task_done_len:
            # List was reset or shrunk; recompute from scratch.
            self._completed_work = float(sum(segments))
            self._last_task_done_len = current_len
        elif current_len > self._last_task_done_len:
            # New segments appended.
            self._completed_work += float(sum(segments[self._last_task_done_len:]))
            self._last_task_done_len = current_len
        # else: same length, assume no change.

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_if_needed()
        self._update_completed_work()

        remaining_work = self.task_duration - self._completed_work
        if remaining_work <= 0.0:
            # Task already complete.
            self._committed_to_od = True
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed

        if remaining_time <= 0.0:
            # Already at or past deadline; nothing can fix it, but choose OD.
            return ClusterType.ON_DEMAND

        slack = remaining_time - remaining_work

        # Decide whether to permanently switch to on-demand.
        if not self._committed_to_od:
            if slack <= self._commit_slack:
                self._committed_to_od = True

        if self._committed_to_od:
            # Once committed, always use on-demand to avoid preemption risk.
            return ClusterType.ON_DEMAND

        # Pre-commit phase: aggressively use spot and spend slack on waiting
        # when spot is unavailable.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)