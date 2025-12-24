from typing import Any, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_balanced_v1"

    def solve(self, spec_path: str) -> "Solution":
        # Internal state initialization
        self._locked_to_on_demand = False
        # Tuning knobs; conservative yet cost-aware
        # Multipliers are applied to guard buffer computation
        self._guard_gap_steps = 3.0  # number of step gaps to keep as buffer
        self._guard_overhead_factor = 1.0  # fraction of restart_overhead to include as buffer
        self._min_guard_seconds = 5 * 60  # minimal guard of 5 minutes
        self._idle_wait_cap_seconds = None  # can be None; optional cap for total idle waiting
        self._total_idle_waited = 0.0
        return self

    def _progress_seconds(self) -> float:
        done = 0.0
        try:
            tdt = self.task_done_time
            if isinstance(tdt, (list, tuple)):
                done = float(sum(tdt))
            else:
                done = float(tdt) if tdt is not None else 0.0
        except Exception:
            done = 0.0
        return max(0.0, min(done, float(self.task_duration)))

    def _guard_buffer(self) -> float:
        # Compute a dynamic guard buffer to protect against discretization and last-moment overhead
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        rh = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        guard_from_gap = gap * self._guard_gap_steps
        guard_from_overhead = rh * self._guard_overhead_factor
        guard = max(guard_from_gap, guard_from_overhead, float(self._min_guard_seconds))
        return guard

    def _remaining_seconds(self) -> float:
        return max(0.0, float(self.task_duration) - self._progress_seconds())

    def _time_left(self) -> float:
        return float(self.deadline) - float(self.env.elapsed_seconds)

    def _should_lock_to_on_demand(self, has_spot: bool) -> bool:
        # Lock when not enough time left to rely on spot or idling without risking deadline
        time_left = self._time_left()
        remaining = self._remaining_seconds()
        guard = self._guard_buffer()

        # If already on on-demand, no further overhead needed; otherwise include one start overhead
        current_is_od = (self.env.cluster_type == ClusterType.ON_DEMAND)
        overhead_needed = 0.0 if current_is_od else float(self.restart_overhead)

        # If time left is less than the sum of remaining work + potential overhead + guard, lock in OD
        if time_left <= remaining + overhead_needed + guard:
            return True

        # If spot not available and we can't afford to wait even a single step, lock to OD
        if not has_spot:
            gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
            # After waiting one step, will we still be safe?
            if (time_left - gap) <= (remaining + float(self.restart_overhead) + guard):
                return True

        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If task is already complete, do nothing
        remaining = self._remaining_seconds()
        if remaining <= 0.0:
            return ClusterType.NONE

        # If we've already committed to on-demand, continue with it
        if self._locked_to_on_demand:
            return ClusterType.ON_DEMAND

        # Determine if we should now lock to on-demand based on safety
        if self._should_lock_to_on_demand(has_spot):
            self._locked_to_on_demand = True
            return ClusterType.ON_DEMAND

        # If spot is available, use it
        if has_spot:
            return ClusterType.SPOT

        # Spot is not available; consider waiting vs switching to OD
        # If we can afford to idle for one step, do so; else switch to OD and lock
        time_left = self._time_left()
        guard = self._guard_buffer()
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        # If there's a configured cap on idle waiting, enforce it
        can_idle_more = True
        if self._idle_wait_cap_seconds is not None:
            can_idle_more = (self._total_idle_waited + gap) <= self._idle_wait_cap_seconds

        if can_idle_more and (time_left - gap) >= (remaining + float(self.restart_overhead) + guard):
            self._total_idle_waited += gap
            return ClusterType.NONE

        # Otherwise, commit to on-demand to ensure we meet the deadline
        self._locked_to_on_demand = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        # Optional tuning parameters
        try:
            parser.add_argument("--guard_gap_steps", type=float, default=3.0)
            parser.add_argument("--guard_overhead_factor", type=float, default=1.0)
            parser.add_argument("--min_guard_seconds", type=float, default=300.0)
            parser.add_argument("--idle_wait_cap_seconds", type=float, default=-1.0)
        except Exception:
            pass
        args, _ = parser.parse_known_args()
        inst = cls(args)
        # Apply parsed configuration if present
        # Guard steps
        try:
            if hasattr(inst, "_guard_gap_steps"):
                inst._guard_gap_steps = float(getattr(args, "guard_gap_steps", inst._guard_gap_steps))
        except Exception:
            pass
        # Overhead factor
        try:
            if hasattr(inst, "_guard_overhead_factor"):
                inst._guard_overhead_factor = float(getattr(args, "guard_overhead_factor", inst._guard_overhead_factor))
        except Exception:
            pass
        # Min guard seconds
        try:
            if hasattr(inst, "_min_guard_seconds"):
                inst._min_guard_seconds = float(getattr(args, "min_guard_seconds", inst._min_guard_seconds))
        except Exception:
            pass
        # Idle wait cap
        try:
            cap = float(getattr(args, "idle_wait_cap_seconds", -1.0))
            if cap is not None and cap >= 0.0:
                inst._idle_wait_cap_seconds = cap
        except Exception:
            pass
        return inst
