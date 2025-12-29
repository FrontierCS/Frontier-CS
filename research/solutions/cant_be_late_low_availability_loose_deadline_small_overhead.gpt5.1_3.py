import math
from typing import Any

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except ImportError:  # Fallback stubs for local testing without sky_spot installed.
    from enum import Enum

    class ClusterType(Enum):
        SPOT = "spot"
        ON_DEMAND = "on_demand"
        NONE = "none"

    class Strategy:
        def __init__(self, args: Any = None):
            # Minimal stub environment; real evaluator will override this.
            class Env:
                elapsed_seconds = 0.0
                gap_seconds = 60.0
                cluster_type = ClusterType.NONE

            self.env = Env()
            self.task_duration = 0.0
            self.task_done_time = []
            self.deadline = 0.0
            self.restart_overhead = 0.0

        def solve(self, spec_path: str):
            return self


class Solution(Strategy):
    NAME = "cant_be_late_safe_spot_aware"

    def __init__(self, args: Any = None):
        super().__init__(args)
        # Per-simulation run state
        self._committed_to_od = False
        self._last_elapsed = None
        self._cached_work_done = 0.0
        self._cached_n_segments = 0

    def solve(self, spec_path: str) -> "Solution":
        # Optional: could parse spec_path if needed. Not required for this strategy.
        return self

    # ---- Internal helpers ----

    def _reset_run_state(self) -> None:
        self._committed_to_od = False
        self._cached_work_done = 0.0
        self._cached_n_segments = 0

    def _get_work_done_estimate(self) -> float:
        """Conservative (never overestimates) estimate of work done in seconds."""
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return self._cached_work_done

        # Handle potential resets of segments between runs.
        n = len(segments)
        if n < self._cached_n_segments:
            # List shrunk; recompute from scratch conservatively.
            self._cached_work_done = 0.0
            self._cached_n_segments = 0

        total = self._cached_work_done
        start_idx = self._cached_n_segments

        for i in range(start_idx, n):
            seg = segments[i]
            if isinstance(seg, (list, tuple)):
                # Interpret as [start, end] interval if possible.
                if len(seg) >= 2:
                    try:
                        start = float(seg[0])
                        end = float(seg[1])
                    except (TypeError, ValueError):
                        continue
                    if end > start:
                        total += end - start
            else:
                # Interpret as a simple duration.
                try:
                    val = float(seg)
                except (TypeError, ValueError):
                    continue
                if val > 0:
                    total += val

        self._cached_work_done = total
        self._cached_n_segments = n

        total_task = getattr(self, "task_duration", None)
        if isinstance(total_task, (int, float)) and total_task > 0 and total > total_task:
            return float(total_task)
        return total

    def _get_remaining_work_estimate(self) -> float:
        total = getattr(self, "task_duration", None)
        if not isinstance(total, (int, float)) or total <= 0:
            return 0.0
        done = self._get_work_done_estimate()
        remaining = total - done
        if remaining < 0.0:
            return 0.0
        return remaining

    # ---- Core decision logic ----

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Detect new simulation run by elapsed time reset.
        current_elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        if self._last_elapsed is None or current_elapsed < self._last_elapsed:
            self._reset_run_state()
        self._last_elapsed = current_elapsed

        # If we've already committed to on-demand, always stay on-demand.
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # If deadline or task_duration are missing, fall back to simple safe policy.
        if not hasattr(self, "deadline") or not hasattr(self, "task_duration"):
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        deadline = float(self.deadline)
        time_left = deadline - current_elapsed

        # Estimate remaining work conservatively (may overestimate).
        remaining_work = self._get_remaining_work_estimate()

        overhead = float(getattr(self, "restart_overhead", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 0.0))

        # Extra safety slack beyond the one-time restart overhead.
        # This guards against discretization and any small estimation errors.
        safety_slack = 4.0 * max(overhead, gap)

        # If there isn't enough slack to safely continue using spot/idle,
        # commit to on-demand for the rest of the run.
        if remaining_work + overhead + safety_slack >= time_left:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Not yet in the fallback on-demand region: be aggressive on spot, idle otherwise.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable and we still have sufficient slack:
        # pause to save cost and rely on future spot or eventual on-demand fallback.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)