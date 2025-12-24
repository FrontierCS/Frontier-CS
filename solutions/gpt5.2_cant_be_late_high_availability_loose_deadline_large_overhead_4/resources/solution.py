import math
from typing import Any, Optional

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:  # pragma: no cover
    from enum import Enum

    class ClusterType(Enum):
        SPOT = "spot"
        ON_DEMAND = "on_demand"
        NONE = "none"

    class Strategy:  # minimal fallback
        def __init__(self, *args, **kwargs):
            self.env = type("Env", (), {"elapsed_seconds": 0.0, "gap_seconds": 60.0, "cluster_type": ClusterType.NONE})()
            self.task_duration = 0.0
            self.task_done_time = []
            self.deadline = 0.0
            self.restart_overhead = 0.0


class Solution(Strategy):
    NAME = "deadline_guard_spot_v1"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except TypeError:
            super().__init__()
        self._initialized = False

        self._p_hat = 0.70
        self._alpha = 0.02

        self._last_has_spot: Optional[bool] = None
        self._spot_true_streak = 0
        self._spot_false_streak = 0
        self._ema_on_steps: float = 20.0
        self._ema_off_steps: float = 5.0
        self._beta = 0.10

        self._od_needed = False
        self._final_od = False

        self._cooldown_steps = 0

        self._td_mode: Optional[str] = None  # "cumulative" or "sum"
        self._td_prev_len = 0
        self._td_sum = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _lazy_init(self) -> None:
        if self._initialized:
            return
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        setup_steps = max(1, int(math.ceil(ro / max(gap, 1e-9))))
        self._ema_on_steps = float(setup_steps + 10)
        self._ema_off_steps = 5.0
        self._initialized = True

    def _update_spot_stats(self, has_spot: bool) -> None:
        self._p_hat = (1.0 - self._alpha) * self._p_hat + self._alpha * (1.0 if has_spot else 0.0)

        if self._last_has_spot is None:
            self._last_has_spot = has_spot
            if has_spot:
                self._spot_true_streak = 1
                self._spot_false_streak = 0
            else:
                self._spot_true_streak = 0
                self._spot_false_streak = 1
            return

        if has_spot == self._last_has_spot:
            if has_spot:
                self._spot_true_streak += 1
            else:
                self._spot_false_streak += 1
            return

        # transition
        if self._last_has_spot:
            # ended an ON streak
            if self._spot_true_streak > 0:
                self._ema_on_steps = (1.0 - self._beta) * self._ema_on_steps + self._beta * float(self._spot_true_streak)
            self._spot_true_streak = 0
            self._spot_false_streak = 1
        else:
            # ended an OFF streak
            if self._spot_false_streak > 0:
                self._ema_off_steps = (1.0 - self._beta) * self._ema_off_steps + self._beta * float(self._spot_false_streak)
            self._spot_false_streak = 0
            self._spot_true_streak = 1

        self._last_has_spot = has_spot

    def _done_work_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0

        if isinstance(td, (int, float)):
            return float(td)

        if not isinstance(td, list) or len(td) == 0:
            return 0.0

        last = td[-1]
        task_dur = float(getattr(self, "task_duration", 0.0) or 0.0)

        # list of numbers
        if isinstance(last, (int, float)):
            lastf = float(last)
            if self._td_mode is None:
                # Decide mode with a small sample
                sample_n = min(20, len(td))
                nums = True
                for i in range(sample_n):
                    if not isinstance(td[i], (int, float)):
                        nums = False
                        break
                if nums:
                    nondecreasing = True
                    for i in range(1, sample_n):
                        if float(td[i]) < float(td[i - 1]) - 1e-9:
                            nondecreasing = False
                            break
                    if nondecreasing and 0.0 <= lastf <= (task_dur * 1.10 + 1e-6):
                        self._td_mode = "cumulative"
                    else:
                        self._td_mode = "sum"
                        self._td_prev_len = 0
                        self._td_sum = 0.0
                else:
                    self._td_mode = "unknown"

            if self._td_mode == "cumulative":
                return max(0.0, min(lastf, task_dur))
            if self._td_mode == "sum":
                cur_len = len(td)
                if cur_len > self._td_prev_len:
                    add = 0.0
                    for x in td[self._td_prev_len:cur_len]:
                        if isinstance(x, (int, float)):
                            add += float(x)
                    self._td_sum += add
                    self._td_prev_len = cur_len
                return max(0.0, min(self._td_sum, task_dur))

            # fallback heuristic
            if len(td) >= 2 and isinstance(td[-2], (int, float)) and lastf >= float(td[-2]) - 1e-9 and lastf <= task_dur * 1.10 + 1e-6:
                return max(0.0, min(lastf, task_dur))
            s = 0.0
            for x in td:
                if isinstance(x, (int, float)):
                    s += float(x)
            return max(0.0, min(s, task_dur))

        # list of (start,end) tuples
        if isinstance(last, (tuple, list)) and len(last) == 2:
            if self._td_mode is None:
                self._td_mode = "pairs"
                self._td_prev_len = 0
                self._td_sum = 0.0
            if self._td_mode == "pairs":
                cur_len = len(td)
                if cur_len > self._td_prev_len:
                    add = 0.0
                    for seg in td[self._td_prev_len:cur_len]:
                        if isinstance(seg, (tuple, list)) and len(seg) == 2:
                            a, b = seg
                            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                                add += max(0.0, float(b) - float(a))
                    self._td_sum += add
                    self._td_prev_len = cur_len
                return max(0.0, min(self._td_sum, task_dur))

        # unknown structure
        return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._update_spot_stats(bool(has_spot))

        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        done = self._done_work_seconds()
        task_dur = float(getattr(self, "task_duration", 0.0) or 0.0)

        remaining_work = max(0.0, task_dur - done)
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        remaining_time = max(0.0, deadline - elapsed)

        # Small safety margin to reduce boundary issues in discrete stepping.
        safety = max(1.0, min(60.0, 0.05 * gap))

        # Hard deadline guard: if OD from now is barely enough, commit to OD.
        od_start_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else ro
        if remaining_time <= remaining_work + od_start_overhead + safety:
            self._final_od = True
            return ClusterType.ON_DEMAND

        if self._final_od:
            return ClusterType.ON_DEMAND

        setup_steps = max(1, int(math.ceil(ro / max(gap, 1e-9))))

        if self._cooldown_steps > 0:
            self._cooldown_steps -= 1

        slack = remaining_time - remaining_work
        p_req = min(1.0, remaining_work / max(remaining_time, 1e-9))

        need_margin = 0.05
        need_od_now = (self._p_hat < p_req * (1.0 + need_margin)) or (slack < ro + gap)

        if need_od_now:
            self._od_needed = True
        else:
            if self._od_needed and (self._p_hat > p_req * 1.15) and (slack > 3.0 * ro):
                self._od_needed = False

        choice: ClusterType

        if has_spot:
            # Prefer spot when available, but avoid frequent OD->SPOT churn.
            if last_cluster_type == ClusterType.SPOT:
                choice = ClusterType.SPOT
            elif last_cluster_type == ClusterType.ON_DEMAND:
                if self._cooldown_steps > 0:
                    choice = ClusterType.ON_DEMAND
                else:
                    k_confirm = min(max(1, setup_steps), 4)
                    exp_remaining_on = max(self._ema_on_steps - float(self._spot_true_streak), 0.0)
                    can_switch = (
                        self._spot_true_streak >= k_confirm
                        and exp_remaining_on >= 0.5 * setup_steps
                        and slack > 2.0 * ro
                    )
                    choice = ClusterType.SPOT if can_switch else ClusterType.ON_DEMAND
            else:
                # last NONE
                choice = ClusterType.SPOT
        else:
            # No spot available
            if self._od_needed:
                choice = ClusterType.ON_DEMAND
            else:
                choice = ClusterType.NONE

        # Enforce rule: cannot return SPOT if has_spot is False
        if (not has_spot) and choice == ClusterType.SPOT:
            choice = ClusterType.ON_DEMAND if self._od_needed else ClusterType.NONE

        # Update cooldown when switching between running cluster types.
        if choice != last_cluster_type and choice in (ClusterType.SPOT, ClusterType.ON_DEMAND):
            self._cooldown_steps = setup_steps

        return choice

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
