import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v2"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._initialized = False
        self._total_steps = 0
        self._spot_available_steps = 0

        self._last_has_spot: Optional[bool] = None
        self._consec_no_spot_steps = 0

        self._spot_up_steps = 0
        self._spot_interruptions = 0

        self._od_mode = False

        # Tunables (seconds). These get finalized once env exists.
        self._base_buffer_enter = None
        self._base_buffer_wait = None
        self._min_p_eff = 0.05

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _safe_float(x: Any, default: float = 0.0) -> float:
        try:
            if x is None:
                return default
            return float(x)
        except Exception:
            return default

    def _work_done_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0
        if isinstance(td, (int, float)):
            return float(td)
        if not isinstance(td, (list, tuple)):
            return 0.0

        total = 0.0
        for seg in td:
            if seg is None:
                continue
            if isinstance(seg, (int, float)):
                total += float(seg)
                continue
            if isinstance(seg, dict):
                if "duration" in seg:
                    total += self._safe_float(seg.get("duration"), 0.0)
                    continue
                if "start" in seg and "end" in seg:
                    total += max(0.0, self._safe_float(seg.get("end")) - self._safe_float(seg.get("start")))
                    continue
                continue
            if isinstance(seg, (list, tuple)) and len(seg) == 2:
                a, b = seg[0], seg[1]
                if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    total += max(0.0, float(b) - float(a))
                    continue
        return total

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        gap = self._safe_float(getattr(self.env, "gap_seconds", 0.0), 0.0)
        ro = self._safe_float(getattr(self, "restart_overhead", 0.0), 0.0)

        one_hour = 3600.0
        self._base_buffer_enter = max(3.0 * ro, one_hour)
        self._base_buffer_wait = max(2.0 * ro, 0.5 * one_hour)

        # If gap is huge, buffers should scale a bit to avoid being overly reactive.
        if gap > 0:
            self._base_buffer_enter = max(self._base_buffer_enter, 2.0 * gap)
            self._base_buffer_wait = max(self._base_buffer_wait, 1.0 * gap)

        self._initialized = True

    def _spot_effective_rate(self) -> float:
        # Estimate effective progress per wall-clock second when using:
        # SPOT if available, otherwise NONE.
        # Incorporates both unavailability and restart overhead due to spot interruptions.
        total = max(self._total_steps, 1)
        p_hat = (self._spot_available_steps + 2.0) / (total + 4.0)  # Laplace smoothing

        gap = self._safe_float(getattr(self.env, "gap_seconds", 0.0), 0.0)
        ro = self._safe_float(getattr(self, "restart_overhead", 0.0), 0.0)

        if gap <= 0:
            return max(min(p_hat, 1.0), self._min_p_eff)

        # Avg contiguous "up" run length in seconds
        interruptions = max(self._spot_interruptions, 1)
        avg_up_steps = self._spot_up_steps / interruptions
        avg_up_seconds = max(avg_up_steps * gap, 1e-9)

        # Overhead reduces effective work during each up-run
        overhead_penalty = max(0.0, 1.0 - (ro / avg_up_seconds))
        p_eff = p_hat * overhead_penalty
        return max(min(p_eff, 1.0), self._min_p_eff)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_initialized()

        # Update availability stats
        self._total_steps += 1
        if has_spot:
            self._spot_available_steps += 1
            self._spot_up_steps += 1
            self._consec_no_spot_steps = 0
        else:
            self._consec_no_spot_steps += 1

        if self._last_has_spot is True and has_spot is False:
            self._spot_interruptions += 1
        self._last_has_spot = has_spot

        elapsed = self._safe_float(getattr(self.env, "elapsed_seconds", 0.0), 0.0)
        gap = self._safe_float(getattr(self.env, "gap_seconds", 0.0), 0.0)
        deadline = self._safe_float(getattr(self, "deadline", 0.0), 0.0)
        task_duration = self._safe_float(getattr(self, "task_duration", 0.0), 0.0)
        ro = self._safe_float(getattr(self, "restart_overhead", 0.0), 0.0)

        done = self._work_done_seconds()
        remaining_work = max(0.0, task_duration - done)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_remaining = max(0.0, deadline - elapsed)
        slack_od = time_remaining - remaining_work

        # Hard fail-safe: if extremely tight, run on-demand.
        # Buffer accounts for potential restart overhead and discrete-step effects.
        tight_buffer = max(self._base_buffer_enter, 3.0 * ro + 2.0 * gap)
        if slack_od <= tight_buffer:
            self._od_mode = True

        # Predict if "spot when available, pause otherwise" is likely enough.
        # If not, commit to on-demand.
        if not self._od_mode:
            p_eff = self._spot_effective_rate()
            expected_calendar_to_finish = remaining_work / p_eff
            # Add a conservative safety term for tail risk and step granularity.
            safety = self._base_buffer_enter + 2.0 * gap
            if expected_calendar_to_finish + safety >= time_remaining:
                self._od_mode = True

        # If spot is extremely choppy (avg up-run shorter than overhead), avoid it when close.
        if not self._od_mode and has_spot:
            if self._spot_interruptions > 0 and gap > 0:
                avg_up_steps = self._spot_up_steps / max(self._spot_interruptions, 1)
                avg_up_seconds = avg_up_steps * gap
                if avg_up_seconds < 2.0 * ro and slack_od < 6.0 * 3600.0:
                    self._od_mode = True

        if self._od_mode:
            return ClusterType.ON_DEMAND

        # Not in OD mode: opportunistically use spot when possible.
        if has_spot:
            return ClusterType.SPOT

        # No spot: wait if we can afford it, otherwise use on-demand.
        # Waiting is cheap but risks deadline; decide based on remaining slack and streak length.
        if gap > 0:
            if time_remaining - gap >= remaining_work + self._base_buffer_wait:
                # If long no-spot streak and slack is shrinking, start OD sooner.
                streak_seconds = self._consec_no_spot_steps * gap
                if streak_seconds >= 2.0 * 3600.0 and slack_od < 10.0 * 3600.0:
                    return ClusterType.ON_DEMAND
                return ClusterType.NONE

        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
