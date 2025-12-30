import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cbl_adaptive_v1"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self._mode = "spot"  # "spot" or "od"
        self._history = []
        self._window_steps: Optional[int] = None
        self._current_down_steps = 0
        self._mean_down_steps: Optional[float] = None

    def solve(self, spec_path: str) -> "Solution":
        self._mode = "spot"
        self._history = []
        self._window_steps = None
        self._current_down_steps = 0
        self._mean_down_steps = None
        return self

    def _work_done_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0
        if isinstance(tdt, (int, float)):
            return float(tdt)
        if not isinstance(tdt, (list, tuple)) or len(tdt) == 0:
            return 0.0

        try:
            all_num = True
            for x in tdt:
                if not isinstance(x, (int, float)):
                    all_num = False
                    break

            if all_num:
                mono = True
                prev = float(tdt[0])
                for x in tdt[1:]:
                    fx = float(x)
                    if fx + 1e-9 < prev:
                        mono = False
                        break
                    prev = fx
                return float(tdt[-1]) if mono else float(sum(float(x) for x in tdt))

            total = 0.0
            for x in tdt:
                if isinstance(x, (int, float)):
                    total += float(x)
                elif isinstance(x, (list, tuple)) and len(x) > 0:
                    v = x[-1]
                    if isinstance(v, (int, float)):
                        total += float(v)
            return total
        except Exception:
            return 0.0

    def _compute_mean_down_steps(self) -> Optional[float]:
        h = self._history
        n = len(h)
        if n < 6:
            return None

        lengths = []
        in_down = not h[0]
        cur = 1 if in_down else 0

        for b in h[1:]:
            if not b:
                if in_down:
                    cur += 1
                else:
                    in_down = True
                    cur = 1
            else:
                if in_down:
                    lengths.append(cur)
                    in_down = False
                    cur = 0

        if in_down:
            lengths.append(cur)

        if not lengths:
            return 0.0
        return float(sum(lengths)) / float(len(lengths))

    def _estimate_effective_spot_rate(self) -> float:
        h = self._history
        n = len(h)
        if n <= 0:
            return 0.2

        true_count = 0
        for b in h:
            if b:
                true_count += 1

        trans = 0
        prev = h[0]
        for b in h[1:]:
            if (not prev) and b:
                trans += 1
            prev = b

        # Conservative priors (low availability regions common).
        alpha_p, beta_p = 2.0, 8.0  # mean=0.2
        p = (true_count + alpha_p) / (n + alpha_p + beta_p)

        alpha_t, beta_t = 1.0, 20.0  # small transition rate prior
        t = (trans + alpha_t) / (n + alpha_t + beta_t)

        gap = float(getattr(self.env, "gap_seconds", 60.0))
        restart = float(getattr(self, "restart_overhead", 0.0))
        oh_frac = (restart / gap) if gap > 1e-9 else 0.0

        eff = p - t * oh_frac
        if eff < 0.01:
            eff = 0.01
        elif eff > 1.0:
            eff = 1.0
        return eff

    def _update_history(self, has_spot: bool) -> None:
        gap = float(getattr(self.env, "gap_seconds", 60.0))
        if self._window_steps is None:
            window_seconds = 6.0 * 3600.0
            self._window_steps = max(12, int(window_seconds / max(gap, 1e-9)))

        b = bool(has_spot)
        self._history.append(b)
        if len(self._history) > self._window_steps:
            self._history.pop(0)

        if b:
            self._current_down_steps = 0
        else:
            self._current_down_steps += 1

        self._mean_down_steps = self._compute_mean_down_steps()

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_history(has_spot)

        work_done = self._work_done_seconds()
        task_duration = float(getattr(self, "task_duration", 0.0))
        work_left = max(0.0, task_duration - work_done)
        if work_left <= 1e-6:
            return ClusterType.NONE

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        deadline = float(getattr(self, "deadline", 0.0))
        time_left = max(0.0, deadline - elapsed)

        gap = float(getattr(self.env, "gap_seconds", 60.0))
        restart = float(getattr(self, "restart_overhead", 0.0))
        buffer = max(2.0 * gap, restart)

        # If we switch to on-demand now, we may pay one restart overhead (worst-case).
        extra_if_switch_to_od = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart
        need_if_od_now = work_left + extra_if_switch_to_od + buffer
        if time_left <= need_if_od_now:
            self._mode = "od"

        if self._mode != "od":
            eff = self._estimate_effective_spot_rate()
            required = (work_left / time_left) if time_left > 1e-9 else 10.0

            # If required progress rate is close to or above expected spot progress, commit to OD.
            if required >= eff * 0.92:
                self._mode = "od"
            else:
                # If currently in a spot-down period, estimate whether we can afford to keep waiting.
                if not has_spot:
                    slack = time_left - work_left
                    md = self._mean_down_steps
                    if md is not None:
                        expected_wait = max(0.0, md - float(self._current_down_steps)) * gap
                        if slack <= expected_wait + restart + buffer:
                            self._mode = "od"

        if self._mode == "od":
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)