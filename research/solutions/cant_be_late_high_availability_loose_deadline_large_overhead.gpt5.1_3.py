import math
from typing import Any, List, Tuple, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "gpt4o_spot_heuristic_v1"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        # Mode: 0 = SPOT_ONLY, 1 = MIXED, 2 = OD_ONLY
        self.mode: int = 0
        self._approx_progress: float = 0.0
        self._last_elapsed: float = 0.0
        # Heuristic thresholds
        default_idle_ratio = 1.35
        default_commit_ratio = 1.10
        default_min_od_run_seconds = 1800.0  # 30 minutes

        self.idle_ratio_threshold: float = getattr(args, "idle_ratio_threshold", default_idle_ratio) if args else default_idle_ratio
        self.commit_ratio_threshold: float = getattr(args, "commit_ratio_threshold", default_commit_ratio) if args else default_commit_ratio
        self.min_od_run_seconds: float = getattr(args, "min_od_run_seconds", default_min_od_run_seconds) if args else default_min_od_run_seconds

        if self.commit_ratio_threshold >= self.idle_ratio_threshold:
            self.commit_ratio_threshold = 0.9 * self.idle_ratio_threshold

        self._od_cooldown_steps: int = 0

    def solve(self, spec_path: str) -> "Solution":
        # Optional: could read config from spec_path; not needed for heuristic.
        return self

    def _compute_progress(self) -> float:
        """Best-effort computation of completed work in seconds from task_done_time."""
        segs = getattr(self, "task_done_time", None)
        if not segs:
            return self._approx_progress

        try:
            first = segs[0]
        except Exception:
            return self._approx_progress

        # Case 1: list of (start, end) segments
        try:
            if isinstance(first, (list, tuple)) and len(first) >= 2:
                total = 0.0
                for seg in segs:
                    if isinstance(seg, (list, tuple)) and len(seg) >= 2:
                        start = float(seg[0])
                        end = float(seg[1])
                        if end > start:
                            total += end - start
                return total
        except Exception:
            pass

        # Case 2: list of numeric durations
        try:
            if isinstance(first, (int, float)):
                return float(sum(float(x) for x in segs))
        except Exception:
            pass

        # Fallback
        return self._approx_progress

    def _update_approx_progress(self, last_cluster_type: ClusterType) -> None:
        """Fallback progress tracker used only if task_done_time is unusable."""
        try:
            gap = float(getattr(self.env, "gap_seconds", 0.0))
        except Exception:
            gap = 0.0

        # Only add work time when on a running cluster.
        if last_cluster_type in (ClusterType.SPOT, ClusterType.ON_DEMAND):
            self._approx_progress += gap

    def _update_mode(self, remaining_work: float, time_remaining: float) -> None:
        """Update scheduling mode based on slack ratio."""
        if remaining_work <= 0:
            return

        restart_overhead = float(getattr(self, "restart_overhead", 0.0))
        req_od_time = remaining_work + restart_overhead
        if req_od_time <= 0:
            return

        slack_ratio = time_remaining / max(req_od_time, 1e-6)

        # Panic: if it's already impossible to finish even with full OD, go OD_ONLY.
        if slack_ratio < 1.0:
            self.mode = 2
            return

        # Monotone mode transitions: 0 -> 1 -> 2
        if self.mode == 0:
            if slack_ratio < self.commit_ratio_threshold:
                self.mode = 2
            elif slack_ratio < self.idle_ratio_threshold:
                self.mode = 1
        elif self.mode == 1:
            if slack_ratio < self.commit_ratio_threshold:
                self.mode = 2

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update fallback progress estimate.
        self._update_approx_progress(last_cluster_type)

        # Fetch environment parameters safely.
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        deadline = float(getattr(self, "deadline", elapsed))
        task_duration = float(getattr(self, "task_duration", 0.0))

        time_remaining = max(deadline - elapsed, 0.0)

        # Estimate progress and remaining work.
        try:
            completed = self._compute_progress()
            remaining_work = max(task_duration - completed, 0.0)
        except Exception:
            completed = self._approx_progress
            remaining_work = max(task_duration - completed, 0.0)

        # If task is done, no need to schedule more.
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Hard deadline passed but work remains: use OD in a last-ditch attempt.
        if time_remaining <= 0.0:
            return ClusterType.ON_DEMAND

        # Update scheduling mode based on current slack.
        self._update_mode(remaining_work, time_remaining)

        # Determine gap and OD cooldown.
        try:
            gap = float(getattr(self.env, "gap_seconds", 0.0))
        except Exception:
            gap = 0.0

        # Main decision logic based on mode.
        if self.mode == 2:
            # OD_ONLY: always use on-demand to guarantee completion.
            return ClusterType.ON_DEMAND

        if self.mode == 1:
            # MIXED mode: primarily use spot, but backstop with OD when spot absent.
            # Implement OD "stickiness" to avoid rapid SPOT<->OD thrashing.
            if self._od_cooldown_steps > 0:
                self._od_cooldown_steps -= 1
                return ClusterType.ON_DEMAND

            if has_spot:
                return ClusterType.SPOT

            # Spot unavailable: use on-demand and start cooldown.
            if gap > 0.0 and self.min_od_run_seconds > 0.0:
                steps = int(math.ceil(self.min_od_run_seconds / max(gap, 1e-6)))
                self._od_cooldown_steps = max(steps - 1, 0)
            return ClusterType.ON_DEMAND

        # mode == 0: SPOT_ONLY mode. Use spot when available, otherwise idle.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        # Optional CLI tunables.
        parser.add_argument("--idle_ratio_threshold", type=float, default=1.35)
        parser.add_argument("--commit_ratio_threshold", type=float, default=1.10)
        parser.add_argument("--min_od_run_seconds", type=float, default=1800.0)
        args, _ = parser.parse_known_args()
        return cls(args)