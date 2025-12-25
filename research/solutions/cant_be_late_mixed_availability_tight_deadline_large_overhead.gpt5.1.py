from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safety_first"

    def __init__(self, args):
        super().__init__(args)
        self._locked_to_od = False
        self._last_elapsed = None

    def solve(self, spec_path: str) -> "Solution":
        # Reset internal state (in case the instance is reused)
        self._locked_to_od = False
        self._last_elapsed = None
        return self

    def _get_done_work(self) -> float:
        """Return a conservative (never overestimating) estimate of work done in seconds."""
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return 0.0

        total_cumulative = 0.0  # for cumulative numeric traces
        total_segmental = 0.0   # for explicit segment durations

        for seg in segments:
            try:
                # Pure numeric: treat as cumulative done time, keep max (monotone assumption).
                if isinstance(seg, (int, float)):
                    val = float(seg)
                    if val > total_cumulative:
                        total_cumulative = val
                    continue

                # Tuple/list representing (start, end)
                if isinstance(seg, (list, tuple)):
                    if len(seg) >= 2 and isinstance(seg[0], (int, float)) and isinstance(seg[1], (int, float)):
                        s = float(seg[0])
                        e = float(seg[1])
                        if e > s:
                            total_segmental += e - s
                        continue

                # Object with start/end attributes
                if hasattr(seg, "start") and hasattr(seg, "end"):
                    s = float(getattr(seg, "start"))
                    e = float(getattr(seg, "end"))
                    if e > s:
                        total_segmental += e - s
                    continue

                # Object with duration attribute
                if hasattr(seg, "duration"):
                    d = float(getattr(seg, "duration"))
                    if d > 0:
                        total_segmental += d
                    continue
            except Exception:
                # Ignore malformed segments conservatively
                continue

        total = max(total_cumulative, total_segmental)
        if total < 0.0:
            total = 0.0

        # Never overestimate beyond task duration
        if hasattr(self, "task_duration"):
            try:
                td = float(self.task_duration)
                if total > td:
                    total = td
            except Exception:
                pass

        return total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Detect new episode based on elapsed time reset
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        if self._last_elapsed is None or elapsed < self._last_elapsed:
            self._locked_to_od = False
        self._last_elapsed = elapsed

        # Compute remaining work
        try:
            task_duration = float(self.task_duration)
        except Exception:
            task_duration = 0.0

        done_work = self._get_done_work()
        remaining = task_duration - done_work
        if remaining <= 0.0:
            return ClusterType.NONE

        # Environment parameters
        try:
            deadline = float(self.deadline)
        except Exception:
            deadline = float("inf")

        gap = float(getattr(self.env, "gap_seconds", 0.0))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))

        # Decide whether we must lock into on-demand to guarantee completion
        if not self._locked_to_od and deadline < float("inf"):
            future_time = elapsed + gap
            slack_after_waste = deadline - future_time - restart_overhead
            # If we cannot afford to waste this step with potentially zero guaranteed progress,
            # we must from now on rely solely on on-demand instances.
            if slack_after_waste < remaining:
                self._locked_to_od = True

        if self._locked_to_od:
            # In lock phase we always use on-demand until completion.
            return ClusterType.ON_DEMAND if remaining > 0.0 else ClusterType.NONE

        # Pre-lock phase: opportunistically use spot; otherwise, safely idle.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)