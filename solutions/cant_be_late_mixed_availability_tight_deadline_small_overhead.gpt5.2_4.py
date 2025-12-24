import math
import json
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self._initialized = False

        self._p_avail = 0.70
        self._spot_on_streak = 0
        self._spot_off_streak = 0

        self._committed_final_od = False
        self._od_lock_until = 0.0

        self._spot_price = None
        self._od_price = None

    def solve(self, spec_path: str) -> "Solution":
        # Optional: try to read prices if present; logic works without it.
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                txt = f.read().strip()
            if txt:
                try:
                    spec = json.loads(txt)
                    self._spot_price = spec.get("spot_price", spec.get("spot", {}).get("price", None))
                    self._od_price = spec.get("on_demand_price", spec.get("on_demand", {}).get("price", None))
                except Exception:
                    pass
        except Exception:
            pass
        return self

    @staticmethod
    def _sum_task_done_time(task_done_time: Any) -> float:
        if task_done_time is None:
            return 0.0
        if isinstance(task_done_time, (int, float)):
            return float(task_done_time)
        # Common cases: list[float] or list[tuple(start,end)].
        try:
            total = 0.0
            for x in task_done_time:
                if isinstance(x, (int, float)):
                    total += float(x)
                elif isinstance(x, (tuple, list)) and len(x) == 2:
                    a, b = x
                    total += float(b) - float(a)
                else:
                    # Fallback: try float conversion
                    total += float(x)
            return float(total)
        except Exception:
            try:
                return float(sum(task_done_time))
            except Exception:
                return 0.0

    def _ensure_init(self) -> None:
        if self._initialized:
            return
        self._initialized = True

    def _final_buffer_seconds(self, gap: float) -> float:
        # Conservative buffer for discretization and a small safety margin.
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        return max(3.0 * gap, 2.0 * ro)

    def _min_od_lock_seconds(self, gap: float) -> float:
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        base = max(900.0, 4.0 * gap, 12.0 * ro)  # >= 15 min, also depends on overhead/step
        if self._p_avail < 0.40:
            base *= 1.5
        elif self._p_avail < 0.60:
            base *= 1.1
        else:
            base *= 0.75
        return min(base, 2.0 * 3600.0)

    def _switch_back_worth_it(self, remaining_work: float, gap: float) -> bool:
        # Heuristic threshold: only switch back to spot if enough work remains.
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        min_work = max(3.0 * 3600.0, 60.0 * ro, 6.0 * gap)
        return remaining_work >= min_work

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()

        now = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        # Update EWMA of availability and streaks
        tau = 2.0 * 3600.0
        alpha = 1.0 - math.exp(-gap / tau) if gap > 0 else 0.05
        obs = 1.0 if has_spot else 0.0
        self._p_avail = (1.0 - alpha) * self._p_avail + alpha * obs

        if has_spot:
            self._spot_on_streak += 1
            self._spot_off_streak = 0
        else:
            self._spot_off_streak += 1
            self._spot_on_streak = 0

        done = self._sum_task_done_time(getattr(self, "task_done_time", None))
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)

        remaining_work = max(0.0, task_duration - done)
        remaining_time = deadline - now

        if remaining_work <= 1e-9:
            return ClusterType.NONE

        # If we can no longer afford anything but continuous on-demand, commit.
        final_buf = self._final_buffer_seconds(gap)
        od_start_overhead = ro if last_cluster_type != ClusterType.ON_DEMAND else 0.0
        min_time_if_od_now = remaining_work + od_start_overhead

        if self._committed_final_od or remaining_time <= min_time_if_od_now + final_buf:
            self._committed_final_od = True
            return ClusterType.ON_DEMAND

        # If we're in an on-demand lock window, keep running on-demand.
        if last_cluster_type == ClusterType.ON_DEMAND and now < self._od_lock_until:
            return ClusterType.ON_DEMAND

        # If currently on-demand (not final), decide whether to switch back to spot.
        if last_cluster_type == ClusterType.ON_DEMAND:
            # Only consider switching back if spot seems stable enough and enough work remains.
            slack = remaining_time - remaining_work
            reserve = final_buf + 2.0 * ro + 2.0 * gap
            if (
                has_spot
                and self._spot_on_streak >= 2
                and self._p_avail >= 0.55
                and slack > reserve + 1800.0
                and self._switch_back_worth_it(remaining_work, gap)
            ):
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # Prefer spot whenever it's available.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: choose between waiting (NONE) and switching to on-demand.
        # Compute an "idle budget" (how much time we can spend with no progress) conservatively.
        # If we idle now, we still expect to pay a restart overhead later to resume compute.
        idle_budget = remaining_time - remaining_work - ro - final_buf

        # If availability is high and the outage is short, wait briefly to avoid on-demand + extra overhead churn.
        if idle_budget > 0.0 and self._p_avail >= 0.65:
            max_short_wait = min(900.0, 0.15 * idle_budget)  # up to 15 min or 15% of budget
            if self._spot_off_streak * gap <= max_short_wait:
                return ClusterType.NONE

        # If we have lots of idle budget and spot is moderately reliable, allow some waiting.
        if idle_budget >= 2.0 * 3600.0 and self._p_avail >= 0.55 and self._spot_off_streak * gap <= 1800.0:
            return ClusterType.NONE

        # Otherwise switch to on-demand (temporarily) to keep progress; lock to avoid thrashing.
        self._od_lock_until = now + self._min_od_lock_seconds(gap)
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
