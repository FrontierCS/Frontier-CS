import math
from typing import Any, Optional

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:  # pragma: no cover
    class Strategy:  # minimal stub for local sanity
        def __init__(self, *args, **kwargs):
            pass

    class ClusterType:
        SPOT = "SPOT"
        ON_DEMAND = "ON_DEMAND"
        NONE = "NONE"


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass

        self._args = args
        self._reset_state()

    def _reset_state(self) -> None:
        self._committed_od = False

        self._prev_has_spot: Optional[bool] = None
        self._current_on_len_s: float = 0.0

        self._on_count: int = 0
        self._on_mean_s: float = 0.0
        self._on_M2: float = 0.0

        self._steps_observed: int = 0
        self._steps_with_spot: int = 0

    def solve(self, spec_path: str) -> "Solution":
        self._reset_state()
        return self

    def _update_availability_stats(self, has_spot: bool, gap_s: float) -> None:
        self._steps_observed += 1
        if has_spot:
            self._steps_with_spot += 1

        if self._prev_has_spot is None:
            self._prev_has_spot = has_spot
            self._current_on_len_s = gap_s if has_spot else 0.0
            return

        if has_spot:
            if self._prev_has_spot:
                self._current_on_len_s += gap_s
            else:
                self._current_on_len_s = gap_s
        else:
            if self._prev_has_spot:
                self._record_on_run(self._current_on_len_s)
            self._current_on_len_s = 0.0

        self._prev_has_spot = has_spot

    def _record_on_run(self, run_len_s: float) -> None:
        x = float(max(0.0, run_len_s))
        if x <= 0.0:
            return
        self._on_count += 1
        if self._on_count == 1:
            self._on_mean_s = x
            self._on_M2 = 0.0
            return
        delta = x - self._on_mean_s
        self._on_mean_s += delta / self._on_count
        delta2 = x - self._on_mean_s
        self._on_M2 += delta * delta2

    def _on_std_s(self) -> float:
        if self._on_count < 2:
            return 0.0
        return math.sqrt(max(0.0, self._on_M2 / (self._on_count - 1)))

    def _mean_on_lcb_s(self, gap_s: float) -> float:
        if self._on_count == 0:
            return max(gap_s, 3600.0)  # assume at least 1 hour until we learn otherwise
        mean_s = self._on_mean_s
        std_s = self._on_std_s()
        # Mildly conservative lower bound; avoid being overly pessimistic early.
        lcb = mean_s - (0.5 * std_s if self._on_count >= 4 else 0.0)
        return max(gap_s, lcb)

    def _get_done_s(self) -> float:
        td = float(getattr(self, "task_duration", 0.0) or 0.0)
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0
        try:
            if isinstance(tdt, (list, tuple)):
                if not tdt:
                    return 0.0
                s = float(sum(float(x) for x in tdt))
                m = float(max(float(x) for x in tdt))
                if s <= td * 1.1:
                    done = s
                else:
                    done = m
            else:
                done = float(tdt)
        except Exception:
            try:
                done = float(tdt[-1])
            except Exception:
                done = 0.0
        if done < 0.0:
            done = 0.0
        if td > 0.0 and done > td:
            done = td
        return done

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed_s = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap_s = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        deadline_s = float(getattr(self, "deadline", 0.0) or 0.0)
        td_s = float(getattr(self, "task_duration", 0.0) or 0.0)
        ro_s = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        self._update_availability_stats(has_spot, gap_s)

        done_s = self._get_done_s()
        remaining_work_s = max(0.0, td_s - done_s)
        remaining_time_s = max(0.0, deadline_s - elapsed_s)

        if remaining_work_s <= 1e-9:
            return ClusterType.NONE

        if remaining_time_s <= 1e-9:
            return ClusterType.NONE

        slack_s = remaining_time_s - remaining_work_s

        # Always guard against missing the deadline.
        if slack_s <= 0.0:
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # Reserve some slack for unexpected restart overheads / last-minute unavailability.
        base_reserve_s = max(900.0, 3.0 * ro_s, 2.0 * gap_s)  # >= 15 minutes
        if self._on_count >= 4:
            # More volatility => keep more reserve.
            mean_on_s = max(gap_s, self._on_mean_s)
            cv = self._on_std_s() / mean_on_s if mean_on_s > 0.0 else 0.0
            base_reserve_s += min(1800.0, 6.0 * ro_s * cv)

        # If slack is extremely tight, remove spot/preemption risk.
        emergency_s = max(600.0, 2.0 * ro_s + gap_s)  # >= 10 minutes

        if self._committed_od or slack_s <= emergency_s:
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # Spot quality: avoid switching into spot if typical spot-on spell is too short
        # relative to restart overhead.
        mean_on_lcb_s = self._mean_on_lcb_s(gap_s)
        avoid_spot_switch = mean_on_lcb_s <= max(2.0 * ro_s, 0.0)

        if has_spot:
            if last_cluster_type != ClusterType.SPOT and avoid_spot_switch and slack_s <= 2.0 * 3600.0:
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # Spot unavailable: spend slack to wait, but keep a reserve.
        if slack_s > base_reserve_s:
            return ClusterType.NONE
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)