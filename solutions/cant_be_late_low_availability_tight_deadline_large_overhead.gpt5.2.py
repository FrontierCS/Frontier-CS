import math
import json
from typing import Any, Optional

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
            self.env = type("Env", (), {"elapsed_seconds": 0.0, "gap_seconds": 300.0, "cluster_type": ClusterType.NONE})()
            self.task_duration = 0.0
            self.task_done_time = []
            self.deadline = 0.0
            self.restart_overhead = 0.0

        def solve(self, spec_path: str):
            return self


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

        self._initialized = False

        self._prev_has_spot: Optional[bool] = None
        self._spot_up_steps = 0
        self._spot_down_steps = 0
        self._ema_up_s = 1800.0
        self._ema_down_s = 1800.0
        self._ema_alpha = 0.20

        self._cooldown_until = -1.0

        self._confirm_steps = 2
        self._risk_buffer_s = 1800.0  # will be set in _lazy_init

        self._spec = {}
        self._args = args

    def solve(self, spec_path: str) -> "Solution":
        if spec_path:
            try:
                with open(spec_path, "r") as f:
                    txt = f.read()
                try:
                    self._spec = json.loads(txt)
                except Exception:
                    self._spec = {}
            except Exception:
                self._spec = {}
        return self

    @staticmethod
    def _is_num(x: Any) -> bool:
        return isinstance(x, (int, float)) and math.isfinite(float(x))

    def _get_work_done_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        td = float(getattr(self, "task_duration", 0.0) or 0.0)

        if tdt is None:
            return 0.0

        if self._is_num(tdt):
            v = float(tdt)
            if td > 0:
                v = max(0.0, min(td, v))
            return v

        if isinstance(tdt, (tuple, list)):
            if not tdt:
                return 0.0

            vals = []
            segsum = 0.0
            any_seg = False
            for x in tdt:
                if self._is_num(x):
                    vals.append(float(x))
                elif isinstance(x, (tuple, list)) and len(x) == 2 and self._is_num(x[0]) and self._is_num(x[1]):
                    a = float(x[0])
                    b = float(x[1])
                    segsum += max(0.0, b - a)
                    any_seg = True

            if any_seg:
                done = segsum
                if td > 0:
                    done = max(0.0, min(td, done))
                return done

            if not vals:
                return 0.0

            s = float(sum(vals))
            last = float(vals[-1])
            nondec = True
            for i in range(1, len(vals)):
                if vals[i] + 1e-9 < vals[i - 1]:
                    nondec = False
                    break

            if td > 0:
                # Heuristic: if vals are cumulative, sum will be much larger than td while last stays <= td.
                if nondec and last <= td + 1e-6 and s > td * 1.2:
                    return max(0.0, min(td, last))
                if s <= td * 1.2:
                    return max(0.0, min(td, s))
                if last <= td * 1.2:
                    return max(0.0, min(td, last))
                return max(0.0, min(td, max(last, s)))

            return max(0.0, max(last, s))

        return 0.0

    def _lazy_init(self) -> None:
        if self._initialized:
            return
        gap = float(getattr(self.env, "gap_seconds", 300.0) or 300.0)
        gap = max(1.0, gap)
        oh = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        # Only switch to spot after it has been continuously available long enough to likely repay restart overhead.
        self._confirm_steps = max(2, int(math.ceil(max(1.0, oh) / gap)))

        # Conservative buffer near deadline to avoid catastrophic penalty.
        self._risk_buffer_s = max(2.0 * oh + 2.0 * gap, 10.0 * gap)

        self._ema_up_s = max(self._ema_up_s, 3.0 * gap)
        self._ema_down_s = max(self._ema_down_s, 3.0 * gap)

        self._initialized = True

    def _update_spot_stats(self, has_spot: bool) -> None:
        gap = float(getattr(self.env, "gap_seconds", 300.0) or 300.0)
        gap = max(1.0, gap)

        if self._prev_has_spot is None:
            self._prev_has_spot = has_spot
            if has_spot:
                self._spot_up_steps = 1
                self._spot_down_steps = 0
            else:
                self._spot_down_steps = 1
                self._spot_up_steps = 0
            return

        if has_spot == self._prev_has_spot:
            if has_spot:
                self._spot_up_steps += 1
            else:
                self._spot_down_steps += 1
            return

        # Transition: finalize previous streak into EMA
        if self._prev_has_spot:
            streak_s = float(self._spot_up_steps) * gap
            self._ema_up_s = (1.0 - self._ema_alpha) * self._ema_up_s + self._ema_alpha * max(gap, streak_s)
            self._spot_up_steps = 0
            self._spot_down_steps = 1
        else:
            streak_s = float(self._spot_down_steps) * gap
            self._ema_down_s = (1.0 - self._ema_alpha) * self._ema_down_s + self._ema_alpha * max(gap, streak_s)
            self._spot_down_steps = 0
            self._spot_up_steps = 1

        self._prev_has_spot = has_spot

    def _should_force_on_demand(self, last_cluster_type: ClusterType, time_left: float, work_left: float) -> bool:
        oh = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        start_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else oh
        # If we're close enough that even one restart or brief instability could cause lateness, lock to OD.
        return time_left <= (work_left + start_overhead + self._risk_buffer_s)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._update_spot_stats(bool(has_spot))

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        time_left = max(0.0, deadline - elapsed)

        total = float(getattr(self, "task_duration", 0.0) or 0.0)
        done = self._get_work_done_seconds()
        work_left = max(0.0, total - done)

        if work_left <= 0.0:
            return ClusterType.NONE

        # If spot just became unavailable while we were on it, back off before trying spot again.
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            oh = float(getattr(self, "restart_overhead", 0.0) or 0.0)
            # Longer cooldown when recent up-streaks are short/unstable.
            instability = 1.0
            if self._ema_up_s > 1e-6:
                instability = min(4.0, max(1.0, (2.0 * oh) / self._ema_up_s))
            cooldown = min(3600.0, max(oh, 2.0 * oh * instability))
            self._cooldown_until = max(self._cooldown_until, elapsed + cooldown)

        # Near deadline, always use OD to avoid the catastrophic penalty.
        if self._should_force_on_demand(last_cluster_type, time_left, work_left):
            return ClusterType.ON_DEMAND

        # If no spot now, run OD (never wait).
        if not has_spot:
            return ClusterType.ON_DEMAND

        # Spot is available now.
        if last_cluster_type == ClusterType.SPOT:
            return ClusterType.SPOT

        # Currently OD or NONE: decide whether to switch to spot.
        oh = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        slack = time_left - work_left
        # Need enough slack to pay at least one restart (switch to spot) while staying safe.
        if slack < (oh + self._risk_buffer_s):
            return ClusterType.ON_DEMAND

        # Cooldown after a preemption.
        if elapsed < self._cooldown_until:
            return ClusterType.ON_DEMAND

        # Require spot to be stable for a minimum duration (in steps) before switching.
        if self._spot_up_steps < self._confirm_steps:
            return ClusterType.ON_DEMAND

        # Require spot streaks to be reasonably long on average.
        if self._ema_up_s < max(1.5 * oh, 2.0 * float(getattr(self.env, "gap_seconds", 300.0) or 300.0)):
            return ClusterType.ON_DEMAND

        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
