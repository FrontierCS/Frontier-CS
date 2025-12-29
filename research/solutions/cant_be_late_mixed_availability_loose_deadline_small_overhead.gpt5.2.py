import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_ema"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._total_steps = 0
        self._spot_steps = 0

        self._last_has_spot: Optional[bool] = None
        self._run_len_steps: int = 0
        self._ema_up_steps: Optional[float] = None
        self._ema_down_steps: Optional[float] = None
        self._ema_alpha: float = 0.2

        self._od_always: bool = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _work_done_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0
        if isinstance(td, (int, float)):
            return float(td)
        if not td:
            return 0.0

        if isinstance(td, (list, tuple)):
            # If list of numeric values, it may be either cumulative or segment durations.
            all_num = True
            nums = []
            for x in td:
                if isinstance(x, (int, float)):
                    nums.append(float(x))
                else:
                    all_num = False
                    break
            if all_num:
                if len(nums) >= 2 and all(nums[i] <= nums[i + 1] for i in range(len(nums) - 1)):
                    # Likely cumulative
                    return float(nums[-1])
                return float(sum(nums))

            total = 0.0
            for x in td:
                if isinstance(x, (int, float)):
                    total += float(x)
                elif isinstance(x, dict):
                    if "duration" in x and isinstance(x["duration"], (int, float)):
                        total += float(x["duration"])
                    elif "start" in x and "end" in x and isinstance(x["start"], (int, float)) and isinstance(
                        x["end"], (int, float)
                    ):
                        total += max(0.0, float(x["end"]) - float(x["start"]))
                elif isinstance(x, (list, tuple)) and len(x) >= 2:
                    a, b = x[0], x[1]
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        # Could be (start, end) or (end, start); take abs diff safely but avoid negative by ordering.
                        aa = float(a)
                        bb = float(b)
                        total += max(0.0, bb - aa) if bb >= aa else max(0.0, aa - bb)
            return float(total)

        return 0.0

    def _update_spot_stats(self, has_spot: bool) -> None:
        self._total_steps += 1
        if has_spot:
            self._spot_steps += 1

        if self._last_has_spot is None:
            self._last_has_spot = has_spot
            self._run_len_steps = 1
            return

        if has_spot == self._last_has_spot:
            self._run_len_steps += 1
            return

        # State change: close out previous run
        ended_state = self._last_has_spot
        run_len = max(1, self._run_len_steps)

        if ended_state:
            if self._ema_up_steps is None:
                self._ema_up_steps = float(run_len)
            else:
                self._ema_up_steps = (1.0 - self._ema_alpha) * self._ema_up_steps + self._ema_alpha * float(run_len)
        else:
            if self._ema_down_steps is None:
                self._ema_down_steps = float(run_len)
            else:
                self._ema_down_steps = (1.0 - self._ema_alpha) * self._ema_down_steps + self._ema_alpha * float(run_len)

        self._last_has_spot = has_spot
        self._run_len_steps = 1

    def _spot_availability_estimate(self) -> float:
        # Beta(1,1) prior for stability early on
        a = 1.0 + float(self._spot_steps)
        b = 1.0 + float(self._total_steps - self._spot_steps)
        return a / (a + b)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_spot_stats(has_spot)

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 1.0))
        deadline = float(getattr(self, "deadline", 0.0))
        task_duration = float(getattr(self, "task_duration", 0.0))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))

        work_done = self._work_done_seconds()
        if work_done >= task_duration - 1e-9:
            return ClusterType.NONE

        remaining_work = max(0.0, task_duration - work_done)
        remaining_time = max(0.0, deadline - elapsed)
        slack_cont = remaining_time - remaining_work

        # If already impossible, still try with on-demand to maximize chance.
        if slack_cont <= 0.0:
            self._od_always = True
            return ClusterType.ON_DEMAND

        # Safety buffer for overheads and variability
        safety = max(6.0 * restart_overhead, 1800.0)  # 6 restarts or 30 minutes

        # Very late: avoid any preemption risk / switching overheads.
        if slack_cont < 2.0 * safety:
            self._od_always = True

        if self._od_always:
            return ClusterType.ON_DEMAND

        p_est = self._spot_availability_estimate()
        p_low = max(0.05, p_est - 0.20)

        # If we run only when spot is available and pause otherwise, expected extra time needed:
        # E[total_time] ~= remaining_work / p_low  => downtime ~= remaining_work*(1/p_low - 1)
        slack_needed_for_pause = remaining_work * (1.0 / p_low - 1.0)

        # If enough slack, do the cheapest: spot when available, otherwise wait.
        if slack_cont >= slack_needed_for_pause + safety:
            return ClusterType.SPOT if has_spot else ClusterType.NONE

        # Otherwise, avoid pauses: compute continuously (use spot when possible).
        if not has_spot:
            return ClusterType.ON_DEMAND

        # has_spot is True:
        # Reduce thrashing: if currently on-demand and spot uptimes are short vs overhead, stick with on-demand.
        overhead_steps = max(1.0, restart_overhead / max(gap, 1.0))
        expected_up = self._ema_up_steps if self._ema_up_steps is not None else 4.0

        if last_cluster_type == ClusterType.ON_DEMAND and expected_up < (overhead_steps + 1.5) and slack_cont < (6.0 * safety):
            return ClusterType.ON_DEMAND

        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)