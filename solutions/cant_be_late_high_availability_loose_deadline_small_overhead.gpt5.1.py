import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_v1"

    def solve(self, spec_path: str) -> "Solution":
        # Initialize persistent state; will also be reset per-environment in _step.
        self._initialized = False
        self.commit_to_od = False
        self._progress_done = 0.0
        self._last_done_len = 0
        self._prev_elapsed = -1.0
        return self

    def _reset_episode_state(self):
        self.commit_to_od = False
        self._progress_done = 0.0
        self._last_done_len = 0
        self._prev_elapsed = self.env.elapsed_seconds
        self._initialized = True

    def _update_progress(self):
        # Incrementally track total work done from task_done_time list.
        if not hasattr(self, "_progress_done"):
            self._progress_done = 0.0
            self._last_done_len = 0
        current_len = len(self.task_done_time)
        if current_len > self._last_done_len:
            # Sum only new segments to keep this O(1) amortized per step.
            new_segments = self.task_done_time[self._last_done_len : current_len]
            if new_segments:
                self._progress_done += sum(new_segments)
            self._last_done_len = current_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Detect new episode / environment reset by elapsed_seconds decreasing.
        if (
            not getattr(self, "_initialized", False)
            or self.env.elapsed_seconds < getattr(self, "_prev_elapsed", -1.0)
        ):
            self._reset_episode_state()
        else:
            self._prev_elapsed = self.env.elapsed_seconds

        # Update cached progress.
        self._update_progress()

        # If task already completed, do nothing.
        if self._progress_done >= self.task_duration:
            return ClusterType.NONE

        # Time left until deadline.
        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0.0:
            # Already at/after deadline; nothing useful to do.
            return ClusterType.NONE

        # Remaining work.
        remaining_work = self.task_duration - self._progress_done
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # If we've committed to on-demand, always keep using it until done.
        if self.commit_to_od:
            return ClusterType.ON_DEMAND

        # Compute minimal continuous on-demand time needed to finish from now.
        time_od_needed = remaining_work

        # Buffer for a potential restart overhead if we switch to OD from a
        # non-OD state (e.g., after spot or NONE). If already on OD, no extra.
        buffer = self.restart_overhead
        if self.env.cluster_type == ClusterType.ON_DEMAND:
            buffer = 0.0

        # Add safety margin for discretization (step granularity).
        step = self.env.gap_seconds
        safe_margin = 2.0 * step

        # If waiting any longer would risk missing the deadline even with full OD,
        # commit to on-demand now.
        if time_left <= time_od_needed + buffer + safe_margin:
            self.commit_to_od = True
            return ClusterType.ON_DEMAND

        # Spot-preferred phase: use spot when available, otherwise wait (NONE).
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
