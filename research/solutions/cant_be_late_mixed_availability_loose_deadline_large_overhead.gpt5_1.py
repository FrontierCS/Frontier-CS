from typing import Any
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cbt_guarded_threshold_v1"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _reset_episode_state(self):
        self._od_locked = False
        self._last_elapsed_seen = -1.0

    def _ensure_state(self):
        if not hasattr(self, "_od_locked"):
            self._reset_episode_state()

    def _compute_done(self) -> float:
        # Sum of completed compute (seconds)
        try:
            return float(sum(self.task_done_time)) if self.task_done_time else 0.0
        except Exception:
            total = 0.0
            for x in self.task_done_time:
                try:
                    total += float(x)
                except Exception:
                    continue
            return total

    def _should_commit_to_od(self) -> bool:
        # Remaining work
        done = self._compute_done()
        remaining_work = max(self.task_duration - done, 0.0)

        # Time left until deadline
        time_left = max(self.deadline - self.env.elapsed_seconds, 0.0)

        # Reaction margin: at least one step to react to preemption + small padding
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        r = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        # Add small padding to account for rounding and scheduling jitter (60s)
        padding = 60.0
        commit_margin = gap + padding

        # We need enough time for remaining work + one restart overhead when starting OD
        need = remaining_work + r + commit_margin

        return time_left <= need + 1e-9

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_state()

        # Detect new episode by elapsed_seconds reset
        if self._last_elapsed_seen is None or self.env.elapsed_seconds < self._last_elapsed_seen:
            self._reset_episode_state()
        self._last_elapsed_seen = self.env.elapsed_seconds

        # If already committed to OD, stay on OD to avoid further overhead and risk.
        if getattr(self, "_od_locked", False):
            return ClusterType.ON_DEMAND

        # Decide if we must commit to OD to meet deadline
        if self._should_commit_to_od():
            self._od_locked = True
            return ClusterType.ON_DEMAND

        # Otherwise, prefer Spot when available; else wait (NONE) to save cost
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)