from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_threshold_v1"

    def solve(self, spec_path: str) -> "Solution":
        # Optional initialization before evaluation.
        # We keep algorithm parameters fixed and lightweight.
        self._initialized_custom = False
        return self

    def _init_custom_state(self):
        if getattr(self, "_initialized_custom", False):
            return
        self._initialized_custom = True
        self._progress_cache_len = 0
        self._progress_total = 0.0
        self._committed_to_od = False

    def _update_progress(self) -> float:
        """Incrementally track total completed work to avoid O(n^2) sums."""
        task_done_time = getattr(self, "task_done_time", None)
        if task_done_time is None:
            return 0.0
        n = len(task_done_time)
        if n > self._progress_cache_len:
            # Sum only new segments.
            self._progress_total += sum(task_done_time[self._progress_cache_len : n])
            self._progress_cache_len = n
        return self._progress_total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_custom_state()

        # Compute remaining work.
        total_work = getattr(self, "task_duration", 0.0)
        progress = self._update_progress()
        remaining_work = max(0.0, total_work - progress)

        # If work is already done (defensive), no need to spend more.
        if remaining_work <= 0.0:
            self._committed_to_od = True
            return ClusterType.NONE

        # Access environment parameters.
        env = self.env
        t = getattr(env, "elapsed_seconds", 0.0)
        gap = max(getattr(env, "gap_seconds", 1.0), 1e-6)
        deadline = getattr(self, "deadline", t + remaining_work)
        overhead = max(getattr(self, "restart_overhead", 0.0), 0.0)

        # Slack = time left after running remaining_work on perfect on-demand.
        slack = deadline - t - remaining_work

        # If slack already non-positive, we're in trouble: go full on-demand.
        if slack <= 0.0:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Total initial slack (from problem spec: deadline - task_duration).
        total_slack = max(0.0, deadline - total_work)

        # Compute conservative thresholds (in seconds).
        # Base margin: multiple of step size and restart overhead.
        base_commit_slack = max(4.0 * gap, 8.0 * overhead)

        if total_slack > 0.0:
            # Commit when slack is a small fraction of total slack, but not too early.
            frac_commit = 0.03 * total_slack  # 3% of total slack.
            commit_slack = max(base_commit_slack, frac_commit)
            commit_slack = min(commit_slack, 0.5 * total_slack)  # never more than half the slack.
        else:
            commit_slack = base_commit_slack

        # Ensure commit_slack >= gap so we cannot skip over zero-slack in a single step.
        commit_slack = max(commit_slack, gap)

        # When spot is unavailable, we start using on-demand earlier to avoid falling behind.
        if total_slack > 0.0:
            extra_pause = min(0.2 * total_slack, 4.0 * 3600.0)  # up to 4 hours or 20% of slack.
        else:
            extra_pause = commit_slack
        pause_slack = max(commit_slack, commit_slack + extra_pause)

        # Latch thresholds for introspection/debugging if needed.
        self._commit_slack = commit_slack
        self._pause_slack = pause_slack

        # Once committed to on-demand, never return to spot or none (until task done).
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Decide whether to commit to ON_DEMAND now (independent of spot availability).
        # Add a small epsilon to be robust to floating-point noise.
        if slack <= commit_slack + 1e-6:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Not yet in final on-demand phase.
        if has_spot:
            # Spot available and we have comfortable slack: use spot.
            return ClusterType.SPOT

        # Spot unavailable: choose between ON_DEMAND and NONE based on slack.
        if slack <= pause_slack + 1e-6:
            # Need to maintain progress to avoid eating too much slack.
            return ClusterType.ON_DEMAND

        # Plenty of slack and no spot: safe (and cheaper) to wait.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
