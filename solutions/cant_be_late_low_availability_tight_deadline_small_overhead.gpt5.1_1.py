from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        # Be robust to different Strategy.__init__ signatures.
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except TypeError:
                pass
        self.args = args
        self.committed = False
        self.commit_slack_sec = None
        self._last_elapsed = None

    def solve(self, spec_path: str) -> "Solution":
        # No special initialization needed; just return self.
        return self

    def _init_commit_slack(self):
        if self.commit_slack_sec is not None:
            return
        # Use environment parameters to set a conservative safety buffer.
        restart = getattr(self, "restart_overhead", 0.0) or 0.0
        gap = getattr(self.env, "gap_seconds", 60.0) if hasattr(self, "env") else 60.0
        base_slack = max(restart, gap)
        # Reserve enough slack to cover at least one gap + one restart,
        # and at least 10 minutes overall.
        self.commit_slack_sec = max(3.0 * base_slack, 10.0 * 60.0)

    def _reset_episode_state_if_needed(self):
        # Detect new episodes by elapsed time reset.
        elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        if self._last_elapsed is None or elapsed < self._last_elapsed:
            # New episode detected.
            self.committed = False
            self.commit_slack_sec = None
        self._last_elapsed = elapsed

    def _total_work_done(self):
        done_segments = getattr(self, "task_done_time", None)
        if done_segments is None:
            return 0.0
        try:
            return float(sum(done_segments))
        except TypeError:
            # Fallback in case it's a single value, not a list.
            try:
                return float(done_segments)
            except (TypeError, ValueError):
                return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Handle per-episode state.
        self._reset_episode_state_if_needed()
        self._init_commit_slack()

        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        time_left = deadline - elapsed

        total_done = self._total_work_done()
        remaining = max(self.task_duration - total_done, 0.0)

        # If work is already done, no need to run more.
        if remaining <= 0.0 or time_left <= 0.0:
            return ClusterType.NONE

        # Decide whether we must commit to on-demand now.
        if not self.committed:
            # If we commit to ON_DEMAND right now, what's the required time?
            # Include a restart overhead if we're not already on ON_DEMAND.
            current_cluster = getattr(self.env, "cluster_type", last_cluster_type)
            if current_cluster == ClusterType.ON_DEMAND:
                overhead_if_commit = 0.0
            else:
                overhead_if_commit = self.restart_overhead

            finish_if_commit = elapsed + overhead_if_commit + remaining
            slack_now = deadline - finish_if_commit

            # If slack is small (or negative), commit to ON_DEMAND.
            if slack_now <= self.commit_slack_sec or time_left <= overhead_if_commit + remaining:
                self.committed = True

        if self.committed:
            # From now on, stay on ON_DEMAND to guarantee completion.
            return ClusterType.ON_DEMAND

        # Not yet committed: use cheap spot when available, otherwise idle.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
