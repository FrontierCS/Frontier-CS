import json
import math
import os
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._last_has_spot: Optional[bool] = None
        self._ema_avail: Optional[float] = None
        self._ema_return: Optional[float] = None

        self._commit_od: bool = False
        self._temp_od: bool = False

        self._cfg = {
            "avail_alpha": 0.02,
            "return_beta": 0.10,
            "min_p_return": 0.05,
            "max_p_return": 0.95,
            "revert_slack_seconds_min": 3600.0,
            "near_finish_keep_od_steps": 6,
            "commit_min_seconds": 1800.0,
        }

    def solve(self, spec_path: str) -> "Solution":
        if spec_path and isinstance(spec_path, str) and os.path.exists(spec_path):
            try:
                with open(spec_path, "r") as f:
                    raw = f.read()
                try:
                    cfg = json.loads(raw)
                except Exception:
                    cfg = None
                if isinstance(cfg, dict):
                    self._cfg.update({k: v for k, v in cfg.items() if k in self._cfg})
            except Exception:
                pass
        return self

    def _numeric_done_from_list(self, lst) -> float:
        nums = []
        for x in lst:
            if isinstance(x, (int, float)) and math.isfinite(x):
                nums.append(float(x))
            elif isinstance(x, (tuple, list)) and len(x) >= 2:
                a, b = x[0], x[1]
                if isinstance(a, (int, float)) and isinstance(b, (int, float)) and math.isfinite(a) and math.isfinite(b):
                    nums.append(float(b) - float(a))
            elif isinstance(x, dict):
                for key in ("duration", "seconds", "done", "work"):
                    v = x.get(key, None)
                    if isinstance(v, (int, float)) and math.isfinite(v):
                        nums.append(float(v))
                        break

        if not nums:
            return 0.0

        is_monotone = True
        for i in range(1, len(nums)):
            if nums[i] + 1e-9 < nums[i - 1]:
                is_monotone = False
                break

        if is_monotone:
            done = nums[-1]
        else:
            done = sum(nums)

        return max(0.0, done)

    def _get_done_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0
        if isinstance(tdt, (int, float)) and math.isfinite(tdt):
            return max(0.0, float(tdt))
        if isinstance(tdt, list):
            return self._numeric_done_from_list(tdt)
        return 0.0

    def _get_remaining_work_seconds(self) -> float:
        total = getattr(self, "task_duration", 0.0)
        if not isinstance(total, (int, float)) or not math.isfinite(total):
            total = 0.0
        total = max(0.0, float(total))
        done = self._get_done_seconds()
        if done > total:
            done = total
        return max(0.0, total - done)

    def _update_spot_stats(self, has_spot: bool) -> None:
        x = 1.0 if has_spot else 0.0
        alpha = float(self._cfg["avail_alpha"])
        if self._ema_avail is None:
            self._ema_avail = x
        else:
            self._ema_avail = (1.0 - alpha) * self._ema_avail + alpha * x

        if self._last_has_spot is False:
            beta = float(self._cfg["return_beta"])
            y = 1.0 if has_spot else 0.0
            if self._ema_return is None:
                self._ema_return = y
            else:
                self._ema_return = (1.0 - beta) * self._ema_return + beta * y

        self._last_has_spot = has_spot

    def _commit_margin_seconds(self, gap: float, restart_overhead: float) -> float:
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        base_slack = max(0.0, deadline - task_duration)

        margin = max(
            2.0 * gap,
            8.0 * restart_overhead,
            0.25 * base_slack,
            float(self._cfg["commit_min_seconds"]),
        )

        p = self._ema_avail if self._ema_avail is not None else 0.65
        if p < 0.60:
            margin *= 1.0 + (0.60 - p) * 1.8
        elif p > 0.80:
            margin *= 0.90

        return margin

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not has_spot and last_cluster_type == ClusterType.SPOT:
            self._temp_od = False

        self._update_spot_stats(bool(has_spot))

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        remaining_work = self._get_remaining_work_seconds()
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        slack = time_left - remaining_work
        commit_margin = self._commit_margin_seconds(gap, restart_overhead)

        if slack <= commit_margin:
            self._commit_od = True

        if self._commit_od:
            self._temp_od = False
            return ClusterType.ON_DEMAND

        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                near_finish_keep = int(self._cfg["near_finish_keep_od_steps"])
                if gap > 0.0 and remaining_work <= near_finish_keep * gap:
                    return ClusterType.ON_DEMAND

            if self._temp_od:
                revert_slack = max(float(self._cfg["revert_slack_seconds_min"]), 12.0 * restart_overhead, 4.0 * gap)
                if slack >= revert_slack and (self._ema_avail or 0.0) >= 0.55:
                    self._temp_od = False
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND

            return ClusterType.SPOT

        p_ret = self._ema_return
        if p_ret is None:
            p_ret = self._ema_avail if self._ema_avail is not None else 0.65
        p_ret = float(min(max(p_ret, float(self._cfg["min_p_return"])), float(self._cfg["max_p_return"])))

        exp_wait = (gap / p_ret) if gap > 0.0 else (restart_overhead / p_ret if restart_overhead > 0.0 else 0.0)
        needed = exp_wait + restart_overhead + commit_margin

        if slack >= needed:
            return ClusterType.NONE

        self._temp_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
