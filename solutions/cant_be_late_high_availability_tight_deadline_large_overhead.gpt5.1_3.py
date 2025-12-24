from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__(args)
        self._policy_initialized = False
        self._commit_slack = None
        self._committed = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _initialize_policy(self):
        # Called on first _step when env is available.
        initial_slack = self.deadline - self.task_duration  # seconds
        gap = getattr(self.env, "gap_seconds", 0.0)
        # Margin to safely cover one worst-case wasted step plus a restart
        commit_margin = self.restart_overhead + 2.0 * gap

        if initial_slack <= 0:
            # No slack at all: must use on-demand from the beginning.
            self._commit_slack = 0.0
        elif initial_slack <= commit_margin:
            # Not enough slack to risk spot usage.
            self._commit_slack = initial_slack
        else:
            # Use the larger of half the slack or the safety margin.
            self._commit_slack = max(0.5 * initial_slack, commit_margin)

        self._policy_initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._policy_initialized:
            self._initialize_policy()

        # Compute remaining work and slack
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed

        work_done = 0.0
        if self.task_done_time:
            work_done = sum(self.task_done_time)

        remaining_work = max(0.0, self.task_duration - work_done)

        # If task is done (or overshot due to numerical issues), do nothing.
        if remaining_work <= 0.0:
            self._committed = True
            return ClusterType.NONE

        slack = remaining_time - remaining_work

        # Commit to on-demand if slack is at or below threshold.
        if (not self._committed) and (slack <= self._commit_slack):
            self._committed = True

        if self._committed:
            # From this point on, always use on-demand to guarantee completion.
            return ClusterType.ON_DEMAND

        # Not yet committed: prefer spot when available; otherwise wait.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
