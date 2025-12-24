import json
import math
from typing import Any, Iterable, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_aware_spot_v1"

    def __init__(self, args=None):
        super().__init__(args)

        # Trace stats
        self._prev_has_spot: Optional[bool] = None
        self._obs_steps: int = 0
        self._spot_avail_steps: int = 0
        self._spot_flips: int = 0
        self._down_flips: int = 0
        self._spot_streak: int = 0
        self._no_spot_streak: int = 0

        # Progress caching
        self._cached_done: float = 0.0
        self._cached_len: int = -1
        self._cached_mode: Optional[str] = None  # "sum" or "max"

        # Config (seconds)
        self._base_reserve: float = 3600.0  # keep at least this much slack
        self._commit_slack: float = 5400.0  # if slack below this -> stay on-demand
        self._stop_od_margin: float = 1800.0  # hysteresis to stop OD during outages
        self._confirm_time: float = 600.0  # require this many seconds of spot availability before switching OD->SPOT

        # Overhead prediction
        self._flip_prior_events: float = 2.0
        self._flip_prior_time: float = 6.0 * 3600.0
        self._overhead_mult: float = 1.3

        # Optional cost info (if provided by spec)
        self._spot_price: Optional[float] = None
        self._od_price: Optional[float] = None

    def solve(self, spec_path: str) -> "Solution":
        try:
            with open(spec_path, "r") as f:
                spec = json.load(f)
            if isinstance(spec, dict):
                cfg = spec.get("config", spec)
                if isinstance(cfg, dict):
                    br = cfg.get("base_reserve_seconds", cfg.get("base_reserve", None))
                    cs = cfg.get("commit_slack_seconds", cfg.get("commit_slack", None))
                    som = cfg.get("stop_od_margin_seconds", cfg.get("stop_od_margin", None))
                    ct = cfg.get("confirm_time_seconds", cfg.get("confirm_time", None))
                    om = cfg.get("overhead_multiplier", cfg.get("overhead_mult", None))
                    if br is not None:
                        self._base_reserve = float(br)
                    if cs is not None:
                        self._commit_slack = float(cs)
                    if som is not None:
                        self._stop_od_margin = float(som)
                    if ct is not None:
                        self._confirm_time = float(ct)
                    if om is not None:
                        self._overhead_mult = float(om)

                    sp = cfg.get("spot_price", None)
                    od = cfg.get("on_demand_price", cfg.get("od_price", None))
                    if sp is not None:
                        self._spot_price = float(sp)
                    if od is not None:
                        self._od_price = float(od)
        except Exception:
            pass
        return self

    def _extract_numeric_list(self, x: Any) -> list:
        if x is None:
            return []
        if isinstance(x, (int, float)):
            return [float(x)]
        if not isinstance(x, (list, tuple)):
            return []
        out = []
        for v in x:
            if v is None:
                continue
            if isinstance(v, (int, float)):
                out.append(float(v))
            elif isinstance(v, (list, tuple)) and len(v) >= 2:
                a, b = v[0], v[1]
                if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    out.append(float(b) - float(a))
        return out

    def _done_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            self._cached_done = 0.0
            self._cached_len = -1
            self._cached_mode = None
            return 0.0

        if isinstance(tdt, (int, float)):
            done = float(tdt)
            self._cached_done = max(0.0, done)
            self._cached_len = -1
            self._cached_mode = None
            return self._cached_done

        if not isinstance(tdt, (list, tuple)):
            return float(self._cached_done) if self._cached_len != -1 else 0.0

        n = len(tdt)
        if n == 0:
            self._cached_done = 0.0
            self._cached_len = 0
            self._cached_mode = "sum"
            return 0.0

        # If first time or list length changed in unexpected way, recompute with heuristic
        if self._cached_len < 0 or n < self._cached_len:
            vals = self._extract_numeric_list(tdt)
            if not vals:
                self._cached_done = 0.0
                self._cached_len = n
                self._cached_mode = "sum"
                return 0.0
            s = sum(vals)
            m = max(vals)
            td = float(getattr(self, "task_duration", 0.0) or 0.0)
            mode = "sum"
            if td > 0:
                if s > td * 1.2 and m <= td * 1.05:
                    mode = "max"
            self._cached_mode = mode
            self._cached_done = m if mode == "max" else s
            self._cached_len = n
            return max(0.0, self._cached_done)

        # Incremental update
        if n == self._cached_len:
            return max(0.0, float(self._cached_done))

        new_part = tdt[self._cached_len :]
        vals = self._extract_numeric_list(new_part)
        if self._cached_mode == "max":
            if vals:
                self._cached_done = max(float(self._cached_done), max(vals))
        else:
            self._cached_done = float(self._cached_done) + sum(vals)

        # Re-validate mode occasionally (cheap heuristic)
        td = float(getattr(self, "task_duration", 0.0) or 0.0)
        if td > 0 and self._cached_mode != "max":
            if float(self._cached_done) > td * 1.2:
                # likely cumulative, fall back to max over full list
                full_vals = self._extract_numeric_list(tdt)
                if full_vals:
                    self._cached_mode = "max"
                    self._cached_done = max(full_vals)

        self._cached_len = n
        return max(0.0, float(self._cached_done))

    def _update_trace_stats(self, has_spot: bool) -> None:
        if self._prev_has_spot is not None:
            if has_spot != self._prev_has_spot:
                self._spot_flips += 1
                if self._prev_has_spot and (not has_spot):
                    self._down_flips += 1
        self._prev_has_spot = has_spot

        self._obs_steps += 1
        if has_spot:
            self._spot_avail_steps += 1
            self._spot_streak += 1
            self._no_spot_streak = 0
        else:
            self._no_spot_streak += 1
            self._spot_streak = 0

    def _compute_reserve(self, remaining_time: float, slack: float, gap: float) -> float:
        base = max(
            float(self._base_reserve),
            5.0 * float(getattr(self, "restart_overhead", 0.0) or 0.0),
            2.0 * gap,
        )

        obs_time = max(1.0, float(self._obs_steps) * gap)
        flip_rate = (float(self._spot_flips) + self._flip_prior_events) / (obs_time + self._flip_prior_time)
        expected_flips = flip_rate * max(0.0, remaining_time)
        exp_overhead = expected_flips * float(getattr(self, "restart_overhead", 0.0) or 0.0)

        reserve = base + self._overhead_mult * exp_overhead

        # Keep reserve reasonable vs available slack (never more than slack unless slack is tiny)
        if slack > 0:
            reserve = min(reserve, slack * 0.95 + base * 0.05)

        return max(base, reserve)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        now = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)

        self._update_trace_stats(has_spot)

        done = self._done_seconds()
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)

        remaining_work = max(0.0, task_duration - done)
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        remaining_time = max(0.0, deadline - now)
        slack = remaining_time - remaining_work

        # If already infeasible or extremely tight, run on-demand
        if remaining_time <= 0.0:
            return ClusterType.NONE
        if slack <= 0.0:
            return ClusterType.ON_DEMAND

        reserve = self._compute_reserve(remaining_time, slack, gap)
        commit_slack = max(float(self._commit_slack), 0.75 * reserve)

        # Near deadline: eliminate risk, stick to on-demand.
        if slack <= commit_slack:
            return ClusterType.ON_DEMAND

        # Confirmation steps for OD -> SPOT switch (avoid flapping)
        confirm_steps = int(math.ceil(max(self._confirm_time, 2.0 * float(getattr(self, "restart_overhead", 0.0) or 0.0)) / max(gap, 1.0)))

        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND and self._spot_streak < confirm_steps:
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # No spot available
        if last_cluster_type == ClusterType.ON_DEMAND:
            if slack > reserve + float(self._stop_od_margin):
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        if slack > reserve:
            return ClusterType.NONE
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
