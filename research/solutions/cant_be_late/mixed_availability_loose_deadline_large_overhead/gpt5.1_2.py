from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cb_late_v1"

    def __init__(self, args):
        super().__init__(args)
        self._reset_internal_state()

    def _reset_internal_state(self):
        self._last_done_list_len = 0
        self._total_work_done = 0.0
        self._prev_elapsed = None

    def solve(self, spec_path: str) -> "Solution":
        # Optional: could read spec_path for configuration; unused here.
        self._reset_internal_state()
        return self

    def _update_progress_cache(self):
        """Incrementally track total work done from task_done_time list."""
        task_done = getattr(self, "task_done_time", None)
        if task_done is None:
            return
        n = len(task_done)
        if n > self._last_done_list_len:
            incremental = 0.0
            # Sum only newly added segments
            for v in task_done[self._last_done_list_len:]:
                try:
                    incremental += float(v)
                except Exception:
                    # Fallback: assume one gap of work if entry is malformed
                    incremental += float(self.env.gap_seconds)
            self._total_work_done += incremental
            self._last_done_list_len = n

    def _maybe_reset_for_new_episode(self):
        """Detect environment reset by checking elapsed_seconds rollback."""
        elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        if self._prev_elapsed is None or elapsed < self._prev_elapsed:
            # New episode detected
            self._reset_internal_state()
        self._prev_elapsed = elapsed

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Detect new episode and reset internal state if needed
        self._maybe_reset_for_new_episode()

        # Update cached total work done
        self._update_progress_cache()

        # Retrieve environment parameters
        elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        gap = getattr(self.env, "gap_seconds", 0.0)
        deadline = getattr(self, "deadline", 0.0)
        restart_overhead = getattr(self, "restart_overhead", 0.0)
        task_duration = getattr(self, "task_duration", 0.0)

        # Pessimistic upper bound on remaining work (seconds)
        remaining = max(task_duration - self._total_work_done, 0.0)

        time_left = deadline - elapsed

        # If no time left or no remaining work (defensive), do nothing.
        if time_left <= 0 or remaining <= 0:
            return ClusterType.NONE

        # Safety margin: at least one gap of slack to account for discretization.
        margin = gap

        # If we're close to deadline, always switch to ON_DEMAND to guarantee completion.
        # We require enough time_left to cover remaining work plus one restart overhead.
        if time_left <= remaining + restart_overhead + margin:
            return ClusterType.ON_DEMAND

        # We have enough slack to use cheaper spot instances opportunistically.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable and we still have slack: wait (NONE) rather than pay for OD now.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)