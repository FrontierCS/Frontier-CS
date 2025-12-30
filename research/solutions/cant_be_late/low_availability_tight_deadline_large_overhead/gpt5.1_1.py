from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_heuristic_v1"

    def __init__(self, args):
        super().__init__(args)
        self.args = args
        self._progress_total = 0.0
        self._last_task_done_len = 0
        self._prev_elapsed = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _update_progress_cache(self):
        segments = self.task_done_time or []
        n = len(segments)
        if n > self._last_task_done_len:
            # Incrementally sum new segments
            self._progress_total += sum(segments[self._last_task_done_len:n])
            self._last_task_done_len = n

    def _reset_episode_state_if_needed(self):
        # Detect new episode by elapsed time reset
        elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        if self._prev_elapsed is None or elapsed < self._prev_elapsed:
            self._progress_total = 0.0
            self._last_task_done_len = 0
        self._prev_elapsed = elapsed

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._reset_episode_state_if_needed()
        self._update_progress_cache()

        elapsed = self.env.elapsed_seconds
        gap = getattr(self.env, "gap_seconds", 0.0)
        deadline = self.deadline
        restart_overhead = getattr(self, "restart_overhead", 0.0) or 0.0

        remaining_wall = max(0.0, deadline - elapsed)

        # Compute remaining work in seconds
        remaining_work = max(0.0, self.task_duration - self._progress_total)

        # If task is done, stop using resources
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # If out of time, still choose ON_DEMAND to try to complete as much as possible
        if remaining_wall <= 0.0:
            return ClusterType.ON_DEMAND

        # Conservative upper bound on time needed if we switch to pure on-demand from now
        # Includes at most one restart overhead from now on.
        min_od_needed = remaining_work + restart_overhead
        if min_od_needed < 0.0:
            min_od_needed = 0.0

        # If even pure on-demand cannot finish, use on-demand anyway
        if remaining_wall < min_od_needed:
            return ClusterType.ON_DEMAND

        # Slack is time we can afford to spend on spot/none before committing to OD
        slack = remaining_wall - min_od_needed

        # Allow at most one potentially unproductive step (of length gap) before we must
        # fall back to on-demand. Add small safety factor for numerical stability.
        safety_factor = 1.05
        slack_threshold = gap * safety_factor

        if slack > slack_threshold:
            # Enough slack to gamble one more step
            if has_spot:
                return ClusterType.SPOT
            else:
                # No spot available and plenty of slack: wait to avoid expensive OD
                return ClusterType.NONE
        else:
            # Slack is tight: use on-demand to guarantee completion
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)