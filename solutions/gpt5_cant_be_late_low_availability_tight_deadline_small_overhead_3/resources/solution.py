from typing import Any, Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_guarded_wait"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        # Configuration with sensible defaults
        self.min_guard_seconds = 900.0  # 15 minutes
        self.overhead_guard_multiplier = 4.0
        self.lock_on_demand_after_threshold = True

        # State variables
        self._prev_elapsed = -1.0
        self._od_latched = False

        # Override defaults if args provided
        if args is not None:
            if hasattr(args, "guard_minutes") and args.guard_minutes is not None:
                try:
                    self.min_guard_seconds = float(args.guard_minutes) * 60.0
                except Exception:
                    pass
            if hasattr(args, "overhead_guard_multiplier") and args.overhead_guard_multiplier is not None:
                try:
                    self.overhead_guard_multiplier = float(args.overhead_guard_multiplier)
                except Exception:
                    pass
            if hasattr(args, "lock_on_demand") and args.lock_on_demand is not None:
                try:
                    self.lock_on_demand_after_threshold = bool(args.lock_on_demand)
                except Exception:
                    pass

    def solve(self, spec_path: str) -> "Solution":
        # Optional: Load external config from spec_path if desired
        # Keep minimal by default; evaluator calls this once before simulation
        return self

    def _reset_if_new_trace(self):
        # Detect a new episode/trace by elapsed time moving backward or to zero
        try:
            current_elapsed = float(self.env.elapsed_seconds)
        except Exception:
            current_elapsed = -1.0

        if self._prev_elapsed < 0 or current_elapsed < self._prev_elapsed or current_elapsed == 0:
            self._od_latched = False

        self._prev_elapsed = current_elapsed

    def _sum_done_seconds(self) -> float:
        total = 0.0
        try:
            segments = self.task_done_time or []
        except Exception:
            return 0.0

        for seg in segments:
            try:
                if isinstance(seg, (list, tuple)):
                    if len(seg) >= 2:
                        a, b = seg[0], seg[1]
                        if a is not None and b is not None:
                            total += max(0.0, float(b) - float(a))
                    elif len(seg) == 1:
                        total += max(0.0, float(seg[0]))
                else:
                    total += max(0.0, float(seg))
            except Exception:
                # Skip malformed entries
                continue
        return max(0.0, total)

    def _guard_time_seconds(self) -> float:
        try:
            gap = float(self.env.gap_seconds)
        except Exception:
            gap = 60.0  # fallback
        try:
            ro = float(self.restart_overhead)
        except Exception:
            ro = 180.0  # 3 minutes default if not provided

        # Guard is the max of min_guard, 2 steps, and k * restart_overhead
        guard = max(self.min_guard_seconds, 2.0 * gap, self.overhead_guard_multiplier * ro)
        return guard

    def _should_lock_to_on_demand(self, remaining_work: float, time_left: float) -> bool:
        guard = self._guard_time_seconds()
        # If we are within the guard window, lock to on-demand
        if time_left <= remaining_work + guard:
            return True
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Ensure episode state is correct
        self._reset_if_new_trace()

        # Compute remaining work and time left
        try:
            total_task = float(self.task_duration)
        except Exception:
            total_task = 0.0
        done = self._sum_done_seconds()
        remaining_work = max(0.0, total_task - done)

        try:
            elapsed = float(self.env.elapsed_seconds)
            deadline = float(self.deadline)
        except Exception:
            elapsed = 0.0
            deadline = float("inf")

        time_left = max(0.0, deadline - elapsed)

        # If task is done, do nothing
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        # If no time left, choose on-demand to mitigate penalty (best effort)
        if time_left <= 0.0:
            self._od_latched = True
            return ClusterType.ON_DEMAND

        # Decide if we need to lock to on-demand to guarantee deadline
        if self.lock_on_demand_after_threshold and not self._od_latched:
            if self._should_lock_to_on_demand(remaining_work, time_left):
                self._od_latched = True

        # If locked to on-demand, stay there
        if self._od_latched:
            return ClusterType.ON_DEMAND

        # Otherwise, prefer spot when available
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: wait if safe, else switch to on-demand
        if self._should_lock_to_on_demand(remaining_work, time_left):
            self._od_latched = True
            return ClusterType.ON_DEMAND

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        # Optional knobs to tune behavior
        parser.add_argument("--guard-minutes", type=float, default=15.0)
        parser.add_argument("--overhead-guard-multiplier", type=float, default=4.0)
        parser.add_argument("--lock-on-demand", action="store_true", default=True)
        args, _ = parser.parse_known_args()
        return cls(args)
