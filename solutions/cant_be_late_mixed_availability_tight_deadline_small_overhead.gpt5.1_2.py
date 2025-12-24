from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__(args)
        self._force_on_demand = False
        self._cached_gap = None
        self._work_done = 0.0
        self._last_td_idx = 0
        self._prev_elapsed = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

    def _reset_episode_state(self):
        self._force_on_demand = False
        self._cached_gap = getattr(self.env, "gap_seconds", None)
        self._work_done = 0.0
        self._last_td_idx = 0

    def _maybe_reset_episode(self):
        elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        if self._prev_elapsed is None or elapsed < self._prev_elapsed:
            self._reset_episode_state()
        self._prev_elapsed = elapsed

    def _update_work_done(self):
        td = getattr(self, "task_done_time", None)
        if not td:
            return
        n = len(td)
        if n > self._last_td_idx:
            # Incrementally sum new segments only
            for i in range(self._last_td_idx, n):
                self._work_done += td[i]
            self._last_td_idx = n

    def _get_gap(self):
        gap = getattr(self.env, "gap_seconds", None)
        if gap is None or gap <= 0.0:
            gap = self._cached_gap
        if gap is None or gap <= 0.0:
            # Try to infer from elapsed time difference
            if self._prev_elapsed is not None:
                inferred = self.env.elapsed_seconds - self._prev_elapsed
                if inferred > 0.0:
                    gap = inferred
        if gap is None or gap <= 0.0:
            # Fallback default (60s) if everything else fails
            gap = 60.0
        self._cached_gap = gap
        return gap

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Detect new trace / episode and reset per-episode state.
        self._maybe_reset_episode()
        # Update cached work-done from environment.
        self._update_work_done()

        # If task already completed, no need to run more.
        remaining_work = max(self.task_duration - self._work_done, 0.0)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        gap = self._get_gap()
        time_left = self.deadline - self.env.elapsed_seconds

        # If somehow out of time, still try to run on-demand to minimize lateness.
        if time_left <= 0.0:
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        # Compute current slack = time_left - remaining_work
        slack = time_left - remaining_work

        # Critical slack to safely risk one more spot step (gap) plus a restart overhead.
        critical_slack = gap + self.restart_overhead

        if not self._force_on_demand and slack <= critical_slack:
            # From now on, we must stick with on-demand to guarantee completion.
            self._force_on_demand = True

        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        # Not yet forced to on-demand:
        # Prefer spot when available; otherwise run on-demand (no pausing).
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND
