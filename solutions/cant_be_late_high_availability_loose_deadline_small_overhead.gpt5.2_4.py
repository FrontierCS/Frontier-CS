import math
import json
import os
from typing import Any, Optional

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:
    from enum import Enum

    class ClusterType(Enum):
        SPOT = "spot"
        ON_DEMAND = "on_demand"
        NONE = "none"

    class Strategy:
        def __init__(self, *args, **kwargs):
            self.env = type("Env", (), {"elapsed_seconds": 0.0, "gap_seconds": 60.0, "cluster_type": ClusterType.NONE})()
            self.task_duration = 0.0
            self.task_done_time = []
            self.deadline = 0.0
            self.restart_overhead = 0.0


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass

        self._cfg = {
            "tau_hours": 4.0,              # EMA time constant
            "p_min": 0.05,                 # clamp for predicted availability
            "p_max": 0.99,
            "spotonly_buffer_mult": 1.5,   # buffer multiplier in feasibility check
            "force_od_buffer_mult": 1.0,   # buffer multiplier in hard guarantee check
            "od_hold_seconds_min": 0.0,    # minimum OD hold time after starting OD
            "od_hold_gap_mult": 2.0,       # hold at least this many gaps worth
            "od_hold_overhead_mult": 4.0,  # hold at least this many overheads worth
            "spot_switch_streak": 2,       # require this many consecutive spot-available steps to switch OD->SPOT
        }

        self._steps = 0
        self._p_ema = 0.65
        self._beta_a = 3.0
        self._beta_b = 2.0
        self._spot_streak = 0
        self._force_od = False
        self._od_hold_steps = 0

    def solve(self, spec_path: str) -> "Solution":
        if spec_path and os.path.exists(spec_path):
            try:
                with open(spec_path, "r", encoding="utf-8") as f:
                    txt = f.read()
                cfg = None
                try:
                    cfg = json.loads(txt)
                except Exception:
                    cfg = None
                if isinstance(cfg, dict):
                    user_cfg = cfg.get("solution_config") or cfg.get("strategy_config") or cfg
                    if isinstance(user_cfg, dict):
                        for k, v in user_cfg.items():
                            if k in self._cfg and isinstance(v, (int, float)):
                                self._cfg[k] = float(v)
            except Exception:
                pass
        return self

    @staticmethod
    def _safe_float(x: Any, default: float = 0.0) -> float:
        try:
            return float(x)
        except Exception:
            return default

    def _get_work_done_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0

        if isinstance(td, (int, float)):
            return float(td)

        if not isinstance(td, list):
            return 0.0

        if not td:
            return 0.0

        total = 0.0
        for seg in td:
            if isinstance(seg, (int, float)):
                total += float(seg)
                continue

            if isinstance(seg, dict):
                for key in ("duration", "work", "done", "seconds", "elapsed", "compute"):
                    if key in seg and isinstance(seg[key], (int, float)):
                        total += float(seg[key])
                        break
                continue

            if isinstance(seg, (tuple, list)):
                if len(seg) >= 2 and isinstance(seg[0], (int, float)) and isinstance(seg[1], (int, float)):
                    total += float(seg[1]) - float(seg[0])
                elif len(seg) == 1 and isinstance(seg[0], (int, float)):
                    total += float(seg[0])

        if total < 0.0:
            total = 0.0
        return total

    def _compute_buffers(self) -> tuple[float, int]:
        gap = self._safe_float(getattr(self.env, "gap_seconds", 0.0), 0.0)
        overhead = self._safe_float(getattr(self, "restart_overhead", 0.0), 0.0)

        buffer_seconds = max(gap, 2.0 * overhead)

        hold_seconds = max(
            self._cfg["od_hold_seconds_min"],
            self._cfg["od_hold_gap_mult"] * gap,
            self._cfg["od_hold_overhead_mult"] * overhead,
        )
        if gap > 0:
            hold_steps = int(math.ceil(hold_seconds / gap))
        else:
            hold_steps = 1
        hold_steps = max(1, min(hold_steps, 48))
        return buffer_seconds, hold_steps

    def _update_availability_estimate(self, has_spot: bool) -> None:
        gap = self._safe_float(getattr(self.env, "gap_seconds", 0.0), 0.0)
        tau = max(60.0, self._cfg["tau_hours"] * 3600.0)
        alpha = gap / (tau + gap) if gap > 0 else 0.05
        alpha = max(0.005, min(alpha, 0.2))

        x = 1.0 if has_spot else 0.0
        self._p_ema = (1.0 - alpha) * self._p_ema + alpha * x

        if has_spot:
            self._beta_a += 1.0
            self._spot_streak += 1
        else:
            self._beta_b += 1.0
            self._spot_streak = 0

        self._steps += 1

    def _p_estimate(self) -> float:
        p_beta = self._beta_a / max(1.0, (self._beta_a + self._beta_b))
        p = 0.7 * self._p_ema + 0.3 * p_beta
        p = max(self._cfg["p_min"], min(self._cfg["p_max"], p))
        return p

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_availability_estimate(has_spot)

        elapsed = self._safe_float(getattr(self.env, "elapsed_seconds", 0.0), 0.0)
        deadline = self._safe_float(getattr(self, "deadline", 0.0), 0.0)
        task_duration = self._safe_float(getattr(self, "task_duration", 0.0), 0.0)
        overhead = self._safe_float(getattr(self, "restart_overhead", 0.0), 0.0)
        gap = self._safe_float(getattr(self.env, "gap_seconds", 0.0), 0.0)

        done = self._get_work_done_seconds()
        if done > task_duration:
            done = task_duration
        work_left = max(0.0, task_duration - done)
        if work_left <= 0.0:
            return ClusterType.NONE

        time_left = max(0.0, deadline - elapsed)

        buffer_seconds, hold_steps = self._compute_buffers()

        # Hard guarantee: if it's getting tight, switch to OD and never leave it.
        if not self._force_od:
            hard_buffer = self._cfg["force_od_buffer_mult"] * buffer_seconds + overhead
            if time_left <= work_left + hard_buffer:
                self._force_od = True

        if self._force_od:
            return ClusterType.ON_DEMAND

        p = self._p_estimate()

        # Feasibility of finishing with "spot when available, pause when unavailable"
        # Expected completion time ~ work_left / p
        spotonly_buffer = self._cfg["spotonly_buffer_mult"] * buffer_seconds
        expected_time_spotonly = work_left / max(p, 1e-6)

        spot_only_feasible = (expected_time_spotonly + spotonly_buffer) <= time_left

        if has_spot:
            # Consider hysteresis when switching OD -> SPOT to avoid flapping-induced overhead.
            if last_cluster_type == ClusterType.ON_DEMAND:
                if self._od_hold_steps > 0:
                    self._od_hold_steps -= 1
                    return ClusterType.ON_DEMAND
                if self._spot_streak < int(self._cfg["spot_switch_streak"]):
                    return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # No spot available.
        if spot_only_feasible:
            # Spend slack by pausing (free), but avoid spending the last bit of slack.
            slack = time_left - work_left
            if slack > (buffer_seconds + gap):
                return ClusterType.NONE
            self._od_hold_steps = hold_steps
            return ClusterType.ON_DEMAND

        # Hybrid mode: rely on OD during spot outages to ensure completion.
        self._od_hold_steps = hold_steps
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
