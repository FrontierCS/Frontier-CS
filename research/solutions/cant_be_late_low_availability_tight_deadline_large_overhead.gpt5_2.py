from typing import Any
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_threshold_v3"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self._committed_to_od = False
        self._last_elapsed = None
        self._base_margin_seconds = 60.0  # baseline safety margin in seconds

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _reset_run_state_if_needed(self):
        cur_elapsed = float(self.env.elapsed_seconds)
        if self._last_elapsed is None or cur_elapsed < (self._last_elapsed or 0.0):
            # New run detected
            self._committed_to_od = False
        self._last_elapsed = cur_elapsed

    def _compute_remaining_work(self) -> float:
        done = 0.0
        try:
            done = float(sum(self.task_done_time)) if self.task_done_time else 0.0
        except Exception:
            done = 0.0
        remaining = float(self.task_duration) - done
        return max(0.0, remaining)

    def _should_commit_to_od(self, last_cluster_type: ClusterType) -> bool:
        # Compute conservative commit threshold based on guaranteed completion
        time_left = max(0.0, float(self.deadline) - float(self.env.elapsed_seconds))
        remaining_work = self._compute_remaining_work()
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        # Safety margin accounts for step discretization and any minor scheduling jitter
        margin = max(self._base_margin_seconds, 2.0 * gap)
        # If already on OD, no switch overhead; else pay restart_overhead on switching
        overhead_to_od = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else float(self.restart_overhead)
        # Commit if not enough time remains to safely wait any longer
        return time_left <= (remaining_work + overhead_to_od + margin)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._reset_run_state_if_needed()

        # If already committed to on-demand, stick to it to avoid extra overhead and risk
        if self._committed_to_od or last_cluster_type == ClusterType.ON_DEMAND:
            # Once on OD, we never go back to spot to avoid re-incurring overhead and risk missing deadline
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # If task is already complete, do nothing
        if self._compute_remaining_work() <= 0.0:
            return ClusterType.NONE

        # Check if we must commit to OD now to guarantee completion
        if self._should_commit_to_od(last_cluster_type):
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Not committed yet: prefer Spot when available
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: determine if we can afford to wait, else switch to OD
        time_left = max(0.0, float(self.deadline) - float(self.env.elapsed_seconds))
        remaining_work = self._compute_remaining_work()
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        margin = max(self._base_margin_seconds, 2.0 * gap)
        # If we wait, we will still need to pay one restart overhead when starting OD later
        slack_to_wait = time_left - (remaining_work + float(self.restart_overhead) + margin)

        if slack_to_wait > 0.0:
            # We can safely wait for Spot to return without risking the deadline
            return ClusterType.NONE

        # No slack left: commit to OD now
        self._committed_to_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)