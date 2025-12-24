import json
import os
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args
        self._reset_internal()

    def _reset_internal(self):
        self._initialized = False

        self._prev_has_spot = None
        self._count_00 = 0
        self._count_01 = 0
        self._count_10 = 0
        self._count_11 = 0

        self._spot_streak = 0
        self._no_spot_streak = 0

        self._forced_od = False
        self._od_hold_until = 0.0

        self._force_od_slack_seconds = 3600.0  # 1 hour
        self._od_hold_seconds = 1800.0  # 30 min
        self._min_spot_streak_to_switch = 2
        self._min_expected_spot_run_seconds = 2700.0  # 45 min
        self._min_slack_switch_seconds = 900.0  # 15 min
        self._max_wait_cap_seconds = 3600.0  # cap waiting expectation at 1 hour
        self._wait_slack_guard_seconds = 300.0  # 5 min

    def solve(self, spec_path: str) -> "Solution":
        if spec_path and os.path.exists(spec_path):
            cfg = None
            try:
                with open(spec_path, "r") as f:
                    txt = f.read()
                try:
                    cfg = json.loads(txt)
                except Exception:
                    cfg = None
                    try:
                        import yaml  # type: ignore
                        cfg = yaml.safe_load(txt)
                    except Exception:
                        cfg = None
            except Exception:
                cfg = None

            if isinstance(cfg, dict):
                self._force_od_slack_seconds = float(
                    cfg.get("force_od_slack_seconds", self._force_od_slack_seconds)
                )
                self._od_hold_seconds = float(cfg.get("od_hold_seconds", self._od_hold_seconds))
                self._min_spot_streak_to_switch = int(
                    cfg.get("min_spot_streak_to_switch", self._min_spot_streak_to_switch)
                )
                self._min_expected_spot_run_seconds = float(
                    cfg.get("min_expected_spot_run_seconds", self._min_expected_spot_run_seconds)
                )
                self._min_slack_switch_seconds = float(
                    cfg.get("min_slack_switch_seconds", self._min_slack_switch_seconds)
                )
                self._max_wait_cap_seconds = float(
                    cfg.get("max_wait_cap_seconds", self._max_wait_cap_seconds)
                )
                self._wait_slack_guard_seconds = float(
                    cfg.get("wait_slack_guard_seconds", self._wait_slack_guard_seconds)
                )
        return self

    def _lazy_init(self):
        if self._initialized:
            return
        self._initialized = True
        self._forced_od = False
        self._od_hold_until = 0.0

    def _get_done_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0
        if isinstance(tdt, (int, float)):
            try:
                return float(tdt)
            except Exception:
                return 0.0
        if not isinstance(tdt, (list, tuple)):
            return 0.0
        if len(tdt) == 0:
            return 0.0

        vals = []
        for x in tdt:
            try:
                vals.append(float(x))
            except Exception:
                continue
        if not vals:
            return 0.0

        monotone = True
        for i in range(len(vals) - 1):
            if vals[i] > vals[i + 1] + 1e-9:
                monotone = False
                break

        s = 0.0
        for v in vals:
            if v > 0:
                s += v

        if monotone:
            # Conservative to avoid overestimating progress:
            # if it's cumulative, last is correct; if it's segments but monotone, last underestimates (safe).
            return max(0.0, vals[-1])
        return max(0.0, s)

    def _p01(self) -> float:
        # P(spot becomes available next step | currently unavailable)
        c0 = self._count_00 + self._count_01
        alpha = 1.0
        return (self._count_01 + alpha) / (c0 + 2.0 * alpha)

    def _p10(self) -> float:
        # P(spot becomes unavailable next step | currently available)
        c1 = self._count_10 + self._count_11
        alpha = 1.0
        return (self._count_10 + alpha) / (c1 + 2.0 * alpha)

    def _expected_wait_for_spot_seconds(self, gap: float) -> float:
        p01 = self._p01()
        if p01 <= 1e-6:
            return self._max_wait_cap_seconds
        steps = 1.0 / p01
        return min(self._max_wait_cap_seconds, steps * gap)

    def _expected_spot_run_seconds(self, gap: float) -> float:
        p10 = self._p10()
        if p10 <= 1e-6:
            return self._max_wait_cap_seconds
        steps = 1.0 / p10
        return min(self._max_wait_cap_seconds, steps * gap)

    def _update_spot_stats(self, has_spot: bool):
        if self._prev_has_spot is None:
            self._prev_has_spot = has_spot
        else:
            prev = self._prev_has_spot
            cur = has_spot
            if (not prev) and (not cur):
                self._count_00 += 1
            elif (not prev) and cur:
                self._count_01 += 1
            elif prev and (not cur):
                self._count_10 += 1
            else:
                self._count_11 += 1
            self._prev_has_spot = has_spot

        if has_spot:
            self._spot_streak += 1
            self._no_spot_streak = 0
        else:
            self._no_spot_streak += 1
            self._spot_streak = 0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        elapsed = float(getattr(getattr(self, "env", None), "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(getattr(self, "env", None), "gap_seconds", 60.0) or 60.0)

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", elapsed + 10**18) or (elapsed + 10**18))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        self._update_spot_stats(bool(has_spot))

        done = self._get_done_seconds()
        if task_duration <= 0.0:
            return ClusterType.NONE

        work_left = task_duration - done
        if work_left <= 1e-6:
            return ClusterType.NONE

        time_left = deadline - elapsed

        if time_left <= 0:
            return ClusterType.NONE

        # Safety buffer for discretization + potential immediate restart.
        buffer = max(2.0 * gap, 0.0) + restart_overhead
        slack = time_left - work_left

        # If we must guarantee completion even if spot never returns, force on-demand.
        if (time_left <= work_left + buffer) or (slack <= self._force_od_slack_seconds):
            self._forced_od = True

        if self._forced_od:
            return ClusterType.ON_DEMAND

        # Not forced OD yet: use spot opportunistically, but avoid churn.
        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                if elapsed < self._od_hold_until:
                    return ClusterType.ON_DEMAND

                if slack < (restart_overhead + self._min_slack_switch_seconds):
                    return ClusterType.ON_DEMAND

                if self._spot_streak < self._min_spot_streak_to_switch:
                    return ClusterType.ON_DEMAND

                exp_run = self._expected_spot_run_seconds(gap)
                if exp_run < self._min_expected_spot_run_seconds:
                    return ClusterType.ON_DEMAND

            return ClusterType.SPOT

        # No spot available now.
        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        exp_wait = self._expected_wait_for_spot_seconds(gap)

        # Wait for spot if we can afford it with slack; otherwise switch to on-demand.
        if slack >= (exp_wait + restart_overhead + self._wait_slack_guard_seconds):
            return ClusterType.NONE

        self._od_hold_until = elapsed + max(self._od_hold_seconds, 3.0 * gap)
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
