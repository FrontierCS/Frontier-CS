import math
from typing import Optional

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:
    from enum import Enum

    class ClusterType(Enum):
        SPOT = 1
        ON_DEMAND = 2
        NONE = 3

    class Strategy:
        def __init__(self, *args, **kwargs):
            self.env = None
            self.task_duration = 0.0
            self.deadline = 0.0
            self.restart_overhead = 0.0


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self._initialized: bool = False

        self._last_elapsed: Optional[float] = None
        self._gap: float = 0.0

        self._done_est: float = 0.0
        self._overhead_left: float = 0.0

        self._total_steps: int = 0
        self._spot_steps: int = 0
        self._prior_alpha: float = 2.0
        self._prior_beta: float = 8.0

        self._prev_has_spot: Optional[bool] = None
        self._spot_streak_len: int = 0
        self._nospot_streak_len: int = 0
        self._avg_spot_streak: float = 3.0
        self._avg_nospot_streak: float = 6.0
        self._streak_ema: float = 0.90

        self._nospot_run_od: bool = False
        self._od_time_accum_steps: float = 0.0

        self._switch_to_spot_min_steps: int = 3
        self._commit_od: bool = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _reset_runtime_state(self) -> None:
        self._initialized = True
        self._last_elapsed = None
        self._done_est = 0.0
        self._overhead_left = 0.0

        self._total_steps = 0
        self._spot_steps = 0

        self._prev_has_spot = None
        self._spot_streak_len = 0
        self._nospot_streak_len = 0
        self._avg_spot_streak = 3.0
        self._avg_nospot_streak = 6.0

        self._nospot_run_od = False
        self._od_time_accum_steps = 0.0

        self._commit_od = False

    def _update_progress_from_last_step(self, last_cluster_type: ClusterType, dt: float) -> None:
        if dt <= 0.0:
            return
        if last_cluster_type == ClusterType.NONE:
            return

        if self._overhead_left > 0.0:
            if self._overhead_left >= dt:
                self._overhead_left -= dt
                return
            else:
                dt -= self._overhead_left
                self._overhead_left = 0.0

        self._done_est += dt
        if self._done_est > self.task_duration:
            self._done_est = self.task_duration

    def _update_streaks(self, has_spot: bool) -> bool:
        new_nospot = False

        if self._prev_has_spot is None:
            if has_spot:
                self._spot_streak_len = 1
                self._nospot_streak_len = 0
            else:
                self._nospot_streak_len = 1
                self._spot_streak_len = 0
                new_nospot = True
        else:
            if has_spot == self._prev_has_spot:
                if has_spot:
                    self._spot_streak_len += 1
                else:
                    self._nospot_streak_len += 1
            else:
                if self._prev_has_spot:
                    if self._spot_streak_len > 0:
                        self._avg_spot_streak = (
                            self._streak_ema * self._avg_spot_streak
                            + (1.0 - self._streak_ema) * float(self._spot_streak_len)
                        )
                    self._spot_streak_len = 0
                    self._nospot_streak_len = 1
                    new_nospot = True
                else:
                    if self._nospot_streak_len > 0:
                        self._avg_nospot_streak = (
                            self._streak_ema * self._avg_nospot_streak
                            + (1.0 - self._streak_ema) * float(self._nospot_streak_len)
                        )
                    self._nospot_streak_len = 0
                    self._spot_streak_len = 1
                    new_nospot = False

        self._prev_has_spot = has_spot
        return new_nospot

    def _p_est(self) -> float:
        denom = self._prior_alpha + self._prior_beta + float(self._total_steps)
        if denom <= 0.0:
            return 0.2
        p = (self._prior_alpha + float(self._spot_steps)) / denom
        if p < 0.01:
            p = 0.01
        elif p > 0.99:
            p = 0.99
        return p

    def _required_od_fraction_unavail(self, remaining_work: float, time_left: float) -> float:
        p = self._p_est()
        expected_spot_work = p * time_left
        expected_unavail = (1.0 - p) * time_left
        if expected_unavail <= 1e-9:
            return 1.0 if remaining_work > expected_spot_work else 0.0

        od_need = remaining_work - expected_spot_work
        if od_need < 0.0:
            od_need = 0.0
        od_need += self.restart_overhead  # cushion for restarts/launches

        f = od_need / expected_unavail
        if f < 0.0:
            f = 0.0
        elif f > 1.0:
            f = 1.0
        return f

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._initialized:
            self._gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
            if self._gap <= 0.0:
                self._gap = 60.0
            self._switch_to_spot_min_steps = max(2, int(math.ceil(self.restart_overhead / self._gap)))
            self._reset_runtime_state()

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)

        if self._last_elapsed is None:
            self._last_elapsed = elapsed
        else:
            if elapsed + 1e-9 < self._last_elapsed:
                self._reset_runtime_state()
                self._last_elapsed = elapsed
            else:
                dt = elapsed - self._last_elapsed
                if dt <= 0.0:
                    dt = self._gap
                self._update_progress_from_last_step(last_cluster_type, dt)
                self._last_elapsed = elapsed

        new_nospot = self._update_streaks(has_spot)

        self._total_steps += 1
        if has_spot:
            self._spot_steps += 1

        time_left = self.deadline - elapsed
        if time_left < 0.0:
            time_left = 0.0

        remaining_work = self.task_duration - self._done_est
        if remaining_work < 0.0:
            remaining_work = 0.0

        if remaining_work <= 0.0:
            self._overhead_left = 0.0
            return ClusterType.NONE

        # Hard feasibility guard (be conservative about at most ~2 more restarts)
        if remaining_work + 2.0 * self.restart_overhead >= time_left:
            self._commit_od = True

        if self._commit_od:
            action = ClusterType.ON_DEMAND
        else:
            if has_spot:
                if last_cluster_type == ClusterType.ON_DEMAND:
                    slack = time_left - remaining_work
                    if self._avg_spot_streak >= float(self._switch_to_spot_min_steps) and slack > (1.5 * self.restart_overhead + self._gap):
                        action = ClusterType.SPOT
                    else:
                        action = ClusterType.ON_DEMAND
                else:
                    action = ClusterType.SPOT
            else:
                f = self._required_od_fraction_unavail(remaining_work, time_left)

                if new_nospot:
                    if last_cluster_type == ClusterType.ON_DEMAND and f > 0.10:
                        self._nospot_run_od = True
                    else:
                        expected_len_steps = max(1.0, float(self._avg_nospot_streak))
                        self._od_time_accum_steps += f * expected_len_steps
                        if self._od_time_accum_steps + 1e-12 >= expected_len_steps:
                            self._nospot_run_od = True
                            self._od_time_accum_steps -= expected_len_steps
                        else:
                            self._nospot_run_od = False

                if f >= 0.95:
                    self._nospot_run_od = True
                elif f <= 0.05 and last_cluster_type != ClusterType.ON_DEMAND:
                    self._nospot_run_od = False

                if last_cluster_type == ClusterType.ON_DEMAND and f > 0.15:
                    self._nospot_run_od = True

                action = ClusterType.ON_DEMAND if self._nospot_run_od else ClusterType.NONE

        if action == ClusterType.SPOT and not has_spot:
            action = ClusterType.ON_DEMAND if self._commit_od else ClusterType.NONE

        if action != ClusterType.NONE and action != last_cluster_type:
            self._overhead_left = float(self.restart_overhead)

        return action

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)