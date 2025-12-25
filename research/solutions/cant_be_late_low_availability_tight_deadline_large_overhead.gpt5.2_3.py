import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_adaptive_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._prev_has_spot: Optional[bool] = None
        self._run_len_sec: float = 0.0
        self._mean_up_sec: Optional[float] = None
        self._mean_down_sec: Optional[float] = None
        self._ewma_alpha: float = 0.05

        self._spot_available_sec: float = 0.0
        self._total_sec: float = 0.0

        self._spot_confirm_sec: float = 0.0

        self._last_switch_time: float = -1e30

        self._od_lock: bool = False

    def solve(self, spec_path: str) -> "Solution":
        self._prev_has_spot = None
        self._run_len_sec = 0.0
        self._mean_up_sec = None
        self._mean_down_sec = None
        self._spot_available_sec = 0.0
        self._total_sec = 0.0
        self._spot_confirm_sec = 0.0
        self._last_switch_time = -1e30
        self._od_lock = False
        return self

    @staticmethod
    def _is_num(x: Any) -> bool:
        return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))

    def _done_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return 0.0
        total = 0.0
        for seg in tdt:
            if seg is None:
                continue
            if self._is_num(seg):
                total += float(seg)
                continue
            if isinstance(seg, (tuple, list)) and len(seg) == 2 and self._is_num(seg[0]) and self._is_num(seg[1]):
                total += float(seg[1]) - float(seg[0])
                continue
            if isinstance(seg, dict):
                if "duration" in seg and self._is_num(seg["duration"]):
                    total += float(seg["duration"])
                    continue
                if "start" in seg and "end" in seg and self._is_num(seg["start"]) and self._is_num(seg["end"]):
                    total += float(seg["end"]) - float(seg["start"])
                    continue
        if total < 0.0:
            total = 0.0
        td = float(getattr(self, "task_duration", 0.0) or 0.0)
        if td > 0.0:
            total = min(total, td)
        return total

    def _update_spot_stats(self, has_spot: bool) -> None:
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if gap <= 0:
            gap = 1.0

        self._total_sec += gap
        if has_spot:
            self._spot_available_sec += gap
            self._spot_confirm_sec += gap
        else:
            self._spot_confirm_sec = 0.0

        if self._prev_has_spot is None:
            self._prev_has_spot = has_spot
            self._run_len_sec = gap
            return

        if has_spot == self._prev_has_spot:
            self._run_len_sec += gap
            return

        # Transition: finalize previous run
        prev_len = self._run_len_sec
        if prev_len <= 0.0:
            prev_len = gap

        if self._prev_has_spot:
            if self._mean_up_sec is None:
                self._mean_up_sec = prev_len
            else:
                a = self._ewma_alpha
                self._mean_up_sec = (1.0 - a) * self._mean_up_sec + a * prev_len
        else:
            if self._mean_down_sec is None:
                self._mean_down_sec = prev_len
            else:
                a = self._ewma_alpha
                self._mean_down_sec = (1.0 - a) * self._mean_down_sec + a * prev_len

        self._prev_has_spot = has_spot
        self._run_len_sec = gap

    def _spot_fraction(self) -> float:
        if self._total_sec <= 0.0:
            return 0.0
        return max(0.0, min(1.0, self._spot_available_sec / self._total_sec))

    def _dynamic_reserve(self, remaining_time: float) -> float:
        o = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        if o <= 0.0:
            return 0.0

        mean_up = self._mean_up_sec if (self._mean_up_sec is not None and self._mean_up_sec > 0) else 1800.0
        mean_down = self._mean_down_sec if (self._mean_down_sec is not None and self._mean_down_sec > 0) else 3600.0
        cycle = max(300.0, mean_up + mean_down)
        expected_cycles = max(0.0, remaining_time / cycle)

        # Conservative but capped: reserve for a handful of future restarts/overheads
        expected_overheads = min(6.0, 1.0 + 0.2 * expected_cycles)
        return o * expected_overheads

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_spot_stats(has_spot)

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if gap <= 0.0:
            gap = 1.0

        done = self._done_seconds()
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        remaining_work = max(0.0, task_duration - done)

        if remaining_work <= 0.0:
            return ClusterType.NONE

        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        remaining_time = deadline - elapsed
        if remaining_time <= 0.0:
            return ClusterType.ON_DEMAND

        o = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        slack_to_go = remaining_time - remaining_work
        reserve = self._dynamic_reserve(remaining_time)

        # If we're close to the deadline, lock to on-demand to avoid restart risk.
        if slack_to_go <= reserve + 0.5 * o:
            self._od_lock = True
        if self._od_lock:
            return ClusterType.ON_DEMAND

        # Dwell time to reduce thrashing
        min_dwell = max(o, 2.0 * gap)

        def can_switch() -> bool:
            return (elapsed - self._last_switch_time) >= min_dwell

        # If we can no longer afford even starting OD later, start OD now.
        # (Extra small margin for the control granularity.)
        overhead_if_start_od_now = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else o
        if remaining_work + overhead_if_start_od_now > remaining_time - 0.25 * gap:
            self._od_lock = True
            return ClusterType.ON_DEMAND

        # Decide actions
        decision: ClusterType

        if has_spot:
            if last_cluster_type == ClusterType.SPOT:
                decision = ClusterType.SPOT
            elif last_cluster_type == ClusterType.ON_DEMAND:
                # Only switch back to spot if (a) we have plenty of slack and (b) spot looks stable.
                mean_up = self._mean_up_sec if (self._mean_up_sec is not None and self._mean_up_sec > 0) else 1800.0
                confirm_needed = max(2.0 * gap, 0.5 * o)
                up_needed = max(2.0 * o, 4.0 * gap)

                enough_slack = slack_to_go > reserve + 2.0 * o
                stable_spot = (self._spot_confirm_sec >= confirm_needed) and (mean_up >= up_needed)

                if enough_slack and stable_spot and can_switch():
                    decision = ClusterType.SPOT
                else:
                    decision = ClusterType.ON_DEMAND
            else:
                # From NONE, take spot when available (cheapest) unless extremely tight (handled above).
                decision = ClusterType.SPOT
        else:
            # No spot available
            if last_cluster_type == ClusterType.ON_DEMAND:
                # Once on OD, keep it running during spot gaps (avoids extra restart overhead).
                decision = ClusterType.ON_DEMAND
            else:
                # If not on OD, consider waiting through the gap if slack allows; otherwise run OD.
                mean_down = self._mean_down_sec if (self._mean_down_sec is not None and self._mean_down_sec > 0) else 3600.0
                p = self._spot_fraction()

                # Margin for waiting while still being able to start OD later.
                # (Assumes at least one restart overhead to start OD later.)
                wait_budget = slack_to_go - reserve - o

                # If spot is extremely scarce and we don't have a big budget, use OD rather than waiting.
                if p < 0.08 and wait_budget < 2.0 * 3600.0:
                    decision = ClusterType.ON_DEMAND
                else:
                    # Wait if we can cover a meaningful portion of a typical downtime.
                    if wait_budget > max(0.5 * o, min(mean_down, 2.0 * o)):
                        decision = ClusterType.NONE
                    else:
                        decision = ClusterType.ON_DEMAND

        if decision != last_cluster_type:
            if (not has_spot) and decision == ClusterType.SPOT:
                decision = ClusterType.ON_DEMAND if last_cluster_type != ClusterType.ON_DEMAND else ClusterType.ON_DEMAND
            else:
                # Apply dwell unless critical.
                if not can_switch():
                    # If we can't switch, stick with last cluster if feasible.
                    if last_cluster_type == ClusterType.SPOT and not has_spot:
                        # Can't keep spot; fallback.
                        decision = ClusterType.ON_DEMAND
                    else:
                        decision = last_cluster_type

        if decision != last_cluster_type:
            self._last_switch_time = elapsed

        return decision

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)