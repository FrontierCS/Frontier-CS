from typing import Any, Dict, List, Sequence

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        # Optional pre-evaluation initialization. We keep it simple.
        return self

    def _compute_work_done(self) -> float:
        """Best-effort computation of total work done based on task_done_time."""
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return 0.0

        total = 0.0
        for seg in segments:
            # Dict-based segment
            if isinstance(seg, dict):
                if "duration" in seg:
                    try:
                        total += float(seg["duration"])
                    except (TypeError, ValueError):
                        continue
                elif "start" in seg and "end" in seg:
                    try:
                        total += float(seg["end"]) - float(seg["start"])
                    except (TypeError, ValueError):
                        continue
                else:
                    # Fallback: try to interpret whole dict as a number
                    try:
                        total += float(seg)  # type: ignore[arg-type]
                    except (TypeError, ValueError):
                        continue
            # Sequence-based segment (e.g., (start, end))
            elif isinstance(seg, (list, tuple)):
                if len(seg) >= 2:
                    try:
                        total += float(seg[1]) - float(seg[0])
                    except (TypeError, ValueError):
                        continue
                elif len(seg) == 1:
                    try:
                        total += float(seg[0])
                    except (TypeError, ValueError):
                        continue
            else:
                # Plain numeric
                try:
                    total += float(seg)  # type: ignore[arg-type]
                except (TypeError, ValueError):
                    continue

        if hasattr(self, "task_duration"):
            try:
                task_duration = float(self.task_duration)
                if total < 0.0:
                    total = 0.0
                elif total > task_duration:
                    total = task_duration
            except (TypeError, ValueError):
                pass
        return total

    def _ensure_internal_state(self) -> None:
        if not hasattr(self, "_committed_to_on_demand"):
            self._committed_to_on_demand = False  # type: ignore[attr-defined]

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_internal_state()

        # If we've already decided to stick with on-demand, do so.
        if self._committed_to_on_demand:  # type: ignore[attr-defined]
            return ClusterType.ON_DEMAND

        # Basic safety checks on environment attributes.
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 0.0))
        deadline = float(getattr(self, "deadline", elapsed))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))
        task_duration = float(getattr(self, "task_duration", 0.0))

        # Compute remaining work.
        work_done = self._compute_work_done()
        remaining_work = task_duration - work_done
        if remaining_work <= 0.0:
            # Task is (or should be) finished; no need to run more.
            return ClusterType.NONE

        # Remaining wall-clock time to deadline.
        remaining_time = deadline - elapsed

        # If we are already out of time, best-effort: run on-demand.
        if remaining_time <= 0.0:
            self._committed_to_on_demand = True  # type: ignore[attr-defined]
            return ClusterType.ON_DEMAND

        # Decide whether it's safe to delay committing to on-demand by one step.
        # If we delay for one gap, worst case:
        #   - we make no additional progress during this gap
        #   - we later pay one restart_overhead, then run entirely on on-demand
        #
        # So it's safe to delay iff:
        #   remaining_time - gap >= remaining_work + restart_overhead
        #
        # We clamp remaining_time - gap at <0 to handle edge cases.
        can_delay = (remaining_time - gap) >= (remaining_work + restart_overhead)

        if has_spot:
            if can_delay:
                # Use spot while it's safe to delay committing to on-demand.
                return ClusterType.SPOT
            else:
                # Not safe to delay further; commit to on-demand from now on.
                self._committed_to_on_demand = True  # type: ignore[attr-defined]
                return ClusterType.ON_DEMAND
        else:
            if can_delay:
                # Safely wait for spot to (maybe) return.
                return ClusterType.NONE
            else:
                # Need to start on-demand now to avoid missing the deadline.
                self._committed_to_on_demand = True  # type: ignore[attr-defined]
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: Any) -> "Solution":
        args, _ = parser.parse_known_args()
        return cls(args)
