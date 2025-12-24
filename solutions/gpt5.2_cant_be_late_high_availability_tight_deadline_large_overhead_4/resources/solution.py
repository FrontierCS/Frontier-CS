import argparse
import json
import math
import os
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self.args = args
        self._initialized = False

        # Online stats about spot availability/outages
        self._total_steps = 0
        self._spot_steps = 0
        self._current_outage_steps = 0
        self._ema_outage_steps = 6.0  # initial guess in steps
        self._ema_alpha = 0.15

        # OD hysteresis
        self._od_min_hold_steps = 2
        self._od_hold_remaining = 0

        # Bookkeeping
        self._last_has_spot = None
        self._last_decision = None

    def solve(self, spec_path: str) -> "Solution":
        # Optional config loading; safe no-op if file missing/unreadable.
        try:
            if spec_path and os.path.exists(spec_path):
                with open(spec_path, "r") as f:
                    txt = f.read()
                try:
                    cfg = json.loads(txt)
                except Exception:
                    cfg = {}
                if isinstance(cfg, dict):
                    alpha = cfg.get("ema_alpha", None)
                    if isinstance(alpha, (int, float)) and 0.01 <= float(alpha) <= 0.5:
                        self._ema_alpha = float(alpha)
                    od_hold = cfg.get("od_min_hold_steps", None)
                    if isinstance(od_hold, int) and 0 <= od_hold <= 100:
                        self._od_min_hold_steps = int(od_hold)
        except Exception:
            pass
        return self

    def _safe_float(self, x: Any, default: float = 0.0) -> float:
        try:
            if x is None:
                return default
            return float(x)
        except Exception:
            return default

    def _compute_done_work(self) -> float:
        td = getattr(self, "task_done_time", None)
        task_duration = self._safe_float(getattr(self, "task_duration", 0.0), 0.0)

        if td is None:
            return 0.0

        if isinstance(td, (int, float)):
            return max(0.0, float(td))

        if not isinstance(td, (list, tuple)):
            return 0.0

        if len(td) == 0:
            return 0.0

        vals = []
        for item in td:
            if isinstance(item, (int, float)):
                vals.append(float(item))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                a = item[0]
                b = item[1]
                if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    vals.append(max(0.0, float(b) - float(a)))
            elif isinstance(item, dict):
                v = item.get("duration", None)
                if isinstance(v, (int, float)):
                    vals.append(float(v))

        if not vals:
            return 0.0

        s = sum(vals)
        m = max(vals)

        # Heuristic: if summing looks too large, interpret as cumulative entries (use max).
        if task_duration > 0.0 and s > task_duration * 1.25 and m <= task_duration * 1.25:
            return max(0.0, m)

        # Otherwise treat as segment durations.
        return max(0.0, s)

    def _init_if_needed(self):
        if self._initialized:
            return
        # If gap is unknown, assume 5 minutes.
        gap = self._safe_float(getattr(getattr(self, "env", None), "gap_seconds", None), 300.0)
        if gap <= 0:
            gap = 300.0
        self._gap_seconds = gap

        ro = self._safe_float(getattr(self, "restart_overhead", None), 0.0)
        if ro < 0:
            ro = 0.0
        self._restart_overhead = ro

        self._initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_if_needed()

        env = getattr(self, "env", None)
        elapsed = self._safe_float(getattr(env, "elapsed_seconds", 0.0), 0.0)
        gap = self._safe_float(getattr(env, "gap_seconds", self._gap_seconds), self._gap_seconds)
        deadline = self._safe_float(getattr(self, "deadline", 0.0), 0.0)
        task_duration = self._safe_float(getattr(self, "task_duration", 0.0), 0.0)
        restart_overhead = self._safe_float(getattr(self, "restart_overhead", self._restart_overhead), 0.0)

        done_work = self._compute_done_work()
        work_left = max(0.0, task_duration - done_work)
        if work_left <= 1e-9:
            self._last_decision = ClusterType.NONE
            return ClusterType.NONE

        time_left = max(0.0, deadline - elapsed)
        slack = time_left - work_left

        # Update online availability/outage stats.
        self._total_steps += 1
        if has_spot:
            self._spot_steps += 1

        if has_spot:
            if self._current_outage_steps > 0:
                self._ema_outage_steps = (
                    self._ema_alpha * float(self._current_outage_steps)
                    + (1.0 - self._ema_alpha) * float(self._ema_outage_steps)
                )
            self._current_outage_steps = 0
        else:
            self._current_outage_steps += 1

        p_avail = (self._spot_steps / self._total_steps) if self._total_steps > 0 else 0.0

        # Safety margins (seconds)
        safety = max(3.0 * restart_overhead, 2.0 * gap, 20.0 * 60.0)
        panic_buffer = max(2.0 * restart_overhead + 6.0 * gap, 45.0 * 60.0)

        # Expected remaining outage time (seconds)
        ema_outage_steps = max(1.0, float(self._ema_outage_steps))
        expected_remaining_outage_steps = max(0.0, ema_outage_steps - float(self._current_outage_steps))
        expected_remaining_outage = expected_remaining_outage_steps * gap

        # Hold OD for a short time once chosen (avoid thrash).
        if last_cluster_type == ClusterType.ON_DEMAND and self._od_hold_remaining > 0:
            self._od_hold_remaining -= 1

        # "Panic" mode: guaranteed completion > cost.
        # Also if spot availability seems very low and slack is not ample, prefer OD.
        if slack <= panic_buffer or (p_avail < 0.55 and slack <= 2.0 * 3600.0):
            self._od_hold_remaining = self._od_min_hold_steps
            self._last_decision = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND

        # If currently on OD and we are still within hold window, keep OD.
        if last_cluster_type == ClusterType.ON_DEMAND and self._od_hold_remaining > 0:
            self._last_decision = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND

        if has_spot:
            # Switch back to spot when we have enough slack to tolerate a restart and a short outage.
            switch_back_buffer = safety + restart_overhead + 2.0 * gap
            if last_cluster_type == ClusterType.ON_DEMAND and slack <= switch_back_buffer:
                self._last_decision = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND
            self._last_decision = ClusterType.SPOT
            return ClusterType.SPOT

        # No spot available this step.
        # Decide to wait (NONE) if slack can cover expected remaining outage + restart + safety.
        wait_need = expected_remaining_outage + restart_overhead + safety
        if slack > wait_need:
            self._last_decision = ClusterType.NONE
            return ClusterType.NONE

        self._od_hold_remaining = self._od_min_hold_steps
        self._last_decision = ClusterType.ON_DEMAND
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        if parser is None:
            parser = argparse.ArgumentParser()
        args, _ = parser.parse_known_args()
        return cls(args)
