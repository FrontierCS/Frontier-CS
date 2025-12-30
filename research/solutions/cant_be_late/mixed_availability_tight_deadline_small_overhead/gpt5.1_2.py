import math
from typing import Any, List, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_v1"

    def __init__(self, args: Any = None):
        # Try to be compatible with different Strategy base signatures.
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except TypeError:
                pass
        self.args = args
        # Tracking for interpreting task_done_time semantics.
        self._task_done_mode: Optional[str] = None  # 'sum' or 'last'
        self._last_task_done_raw: Optional[List[float]] = None
        self._progress_estimate: float = 0.0

    def solve(self, spec_path: str) -> "Solution":
        # No offline initialization; stateless heuristic.
        return self

    def _compute_progress(self) -> float:
        """Estimate total task progress from self.task_done_time."""
        raw = getattr(self, "task_done_time", None)
        if raw is None:
            return self._progress_estimate

        # Handle non-list types defensively (e.g., a single float)
        if not isinstance(raw, (list, tuple)):
            try:
                v = float(raw)
            except (TypeError, ValueError):
                return self._progress_estimate
            if v >= self._progress_estimate:
                td = float(getattr(self, "task_duration", self._progress_estimate))
                self._progress_estimate = min(v, td)
            return self._progress_estimate

        raw_list = list(raw)

        # If the list is very long, it's likely a time series of cumulative
        # progress; assume 'last' mode to avoid O(n) scans every step.
        if self._task_done_mode is None and len(raw_list) > 1000:
            self._task_done_mode = "last"

        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        tol = 1e-6

        # Try to infer representation mode from consecutive observations.
        if (
            self._last_task_done_raw is not None
            and self._task_done_mode is None
            and self._last_task_done_raw
            and raw_list
        ):
            prev = self._last_task_done_raw
            # Precompute previous aggregates
            sum_prev = float(sum(prev))
            last_prev = float(prev[-1])
            # Current aggregates
            sum_now = float(sum(raw_list))
            last_now = float(raw_list[-1])

            delta_sum = sum_now - sum_prev
            delta_last = last_now - last_prev

            # Reasonable upper bound on per-step progress increment.
            max_delta = max(gap * 1.5, 1.0)

            valid_sum = (-tol <= delta_sum <= max_delta)
            valid_last = (-tol <= delta_last <= max_delta)

            if valid_sum and not valid_last:
                self._task_done_mode = "sum"
            elif valid_last and not valid_sum:
                self._task_done_mode = "last"
            # If both valid or both invalid, remain undecided.

        # Compute candidate progress based on current interpretation.
        if self._task_done_mode == "sum":
            candidate = float(sum(raw_list))
        elif self._task_done_mode == "last":
            candidate = float(raw_list[-1]) if raw_list else 0.0
        else:
            # Conservative while undecided: never over-estimate progress.
            total = float(sum(raw_list)) if raw_list else 0.0
            last_val = float(raw_list[-1]) if raw_list else 0.0
            candidate = min(total, last_val)

        # Ensure monotonicity and clamp to task duration.
        if candidate + tol < self._progress_estimate:
            candidate = self._progress_estimate
        tduration = float(getattr(self, "task_duration", candidate))
        self._progress_estimate = min(candidate, tduration)

        self._last_task_done_raw = raw_list
        return self._progress_estimate

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Estimate how much of the task is completed.
        try:
            progress = float(self._compute_progress())
        except Exception:
            progress = float(getattr(self, "_progress_estimate", 0.0))

        task_duration = float(getattr(self, "task_duration", 0.0))
        deadline = float(getattr(self, "deadline", 0.0))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))

        env = getattr(self, "env", None)
        if env is None:
            # Fallback: no environment, default to safe on-demand usage.
            return ClusterType.ON_DEMAND

        elapsed = float(getattr(env, "elapsed_seconds", 0.0))
        gap = float(getattr(env, "gap_seconds", 0.0) or 0.0)

        remaining_work = max(task_duration - progress, 0.0)
        time_left = deadline - elapsed

        # If job is done or no time remains, do nothing.
        if remaining_work <= 0.0 or time_left <= 0.0:
            return ClusterType.NONE

        # Slack = how much extra time beyond pure on-demand we have.
        slack = time_left - remaining_work

        # If it's already impossible to finish even with full on-demand,
        # minimize cost: prefer spot if available, otherwise idle.
        if slack < 0.0:
            return ClusterType.SPOT if has_spot else ClusterType.NONE

        # Compute a minimum slack required to safely "gamble" on spot or idling
        # for one more step, accounting for:
        #   - one gap of zero progress
        #   - one restart overhead before resuming on-demand
        total_slack = max(deadline - task_duration, 0.0)
        extra_buffer = 0.1 * total_slack  # additional safety margin
        min_slack_for_risk = gap + restart_overhead + extra_buffer

        # Cap the required slack to total_slack so we don't become over-strict.
        if total_slack > 0.0:
            min_slack_for_risk = min(min_slack_for_risk, total_slack)

        risk_allowed = slack > max(min_slack_for_risk, 0.0)

        if risk_allowed:
            # With sufficient slack, exploit spot aggressively and otherwise wait.
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE

        # Slack is low: switch to on-demand to guarantee completion.
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)