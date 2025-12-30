from typing import Any, Iterable
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_threshold_v1"

    def solve(self, spec_path: str) -> "Solution":
        # Optional initialization; not using spec_path for now.
        return self

    def _estimate_progress(self) -> float:
        """Estimate total completed task duration from self.task_done_time."""
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return 0.0

        total = 0.0

        try:
            # Peek first element to infer structure.
            first = segments[0]
        except (IndexError, TypeError):
            return 0.0

        try:
            if isinstance(first, (tuple, list)):
                # Interpret as (start, end) style segments.
                for seg in segments:  # type: ignore[assignment]
                    if not seg:
                        continue
                    try:
                        start = float(seg[0])
                        end = float(seg[1])
                        length = end - start
                        if length > 0.0:
                            total += length
                    except (TypeError, ValueError, IndexError):
                        continue
            else:
                # Interpret as list of lengths.
                for seg in segments:  # type: ignore[assignment]
                    try:
                        val = float(seg)
                        if val > 0.0:
                            total += val
                    except (TypeError, ValueError):
                        continue
        except TypeError:
            # segments not iterable
            return 0.0

        if total < 0.0:
            total = 0.0

        # Cap at task_duration if available.
        try:
            duration = float(getattr(self, "task_duration", 0.0) or 0.0)
            if duration > 0.0 and total > duration:
                total = duration
        except (TypeError, ValueError):
            pass

        return total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Fallback simple strategy if environment attributes are missing.
        env = getattr(self, "env", None)
        if env is None:
            return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND

        # Basic environment parameters.
        try:
            elapsed = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
        except (TypeError, ValueError):
            elapsed = 0.0

        try:
            gap = float(getattr(env, "gap_seconds", 0.0) or 0.0)
        except (TypeError, ValueError):
            gap = 0.0

        # Core problem parameters.
        try:
            deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        except (TypeError, ValueError):
            deadline = 0.0

        try:
            task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        except (TypeError, ValueError):
            task_duration = 0.0

        try:
            restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        except (TypeError, ValueError):
            restart_overhead = 0.0

        # If parameters are not set, fall back to naive strategy.
        if deadline <= 0.0 or task_duration <= 0.0 or gap <= 0.0:
            return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND

        # Compute current progress and remaining work.
        progress = self._estimate_progress()
        remaining_work = max(0.0, task_duration - progress)

        # If job is already completed (or numerically very close), stop.
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_remaining = max(0.0, deadline - elapsed)

        # If somehow out of time, best effort is to keep running on-demand.
        if time_remaining <= 0.0:
            return ClusterType.ON_DEMAND

        # Hard feasibility check: even if we switch to on-demand now and pay one
        # restart overhead, can we finish in time?
        # Condition for feasibility: time_remaining - restart_overhead >= remaining_work
        if time_remaining - restart_overhead < remaining_work:
            # Already in a precarious state; always choose on-demand to maximize chance.
            return ClusterType.ON_DEMAND

        # Decide whether we can afford to "risk" this step with potentially no progress.
        #
        # Worst case if we risk (use SPOT or NONE):
        #   - We lose `gap` seconds of wall time with zero task progress.
        #   - After that, we may need one restart_overhead before reliable OD.
        #
        # We require that even in this worst case, we can still complete:
        #   time_remaining - gap - restart_overhead >= remaining_work
        if time_remaining - gap - restart_overhead >= remaining_work:
            # Safe to risk this step: prefer cheaper spot if available, else pause.
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE
        else:
            # Cannot afford to lose this gap; must run on reliable on-demand.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: Any) -> "Solution":
        args, _ = parser.parse_known_args()
        return cls(args)