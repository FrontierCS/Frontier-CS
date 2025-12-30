import math
from typing import Any, Optional

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:  # pragma: no cover
    class Strategy:  # minimal fallback
        def __init__(self, args=None):
            self.args = args
            self.env = type("Env", (), {"elapsed_seconds": 0.0, "gap_seconds": 1.0, "cluster_type": None})()
            self.task_duration = 0.0
            self.task_done_time = []
            self.deadline = 0.0
            self.restart_overhead = 0.0

    class ClusterType:
        SPOT = "SPOT"
        ON_DEMAND = "ON_DEMAND"
        NONE = "NONE"


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._prev_elapsed_raw: Optional[float] = None
        self._time_scale: float = 1.0

        # Availability statistics
        self._steps: int = 0
        self._spot_steps: int = 0
        self._p_ewma: float = 0.5
        self._p_ewma_alpha: float = 0.05
        self._last_has_spot: Optional[bool] = None
        self._tf_transitions: int = 0
        self._true_steps_for_hazard: int = 0
        self._avail_streak: int = 0
        self._unavail_streak: int = 0

        # Run streak of chosen cluster type
        self._run_type: Optional[ClusterType] = None
        self._run_len: int = 0

        # OD pacing
        self._od_debt: float = 0.0

        # Deadline safety mode
        self._od_lock: bool = False

        # Switching commitment (avoid thrashing during restart overhead)
        self._commit_type: Optional[ClusterType] = None
        self._commit_remaining: int = 0
        self._overhead_steps: int = 1

        # task_done_time cache
        self._tdt_cache_len: int = 0
        self._tdt_cache_done: float = 0.0
        self._tdt_cache_kind: str = "unknown"  # "segments", "cumulative", "increments", "unknown"

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _is_number(x: Any) -> bool:
        return isinstance(x, (int, float)) and not isinstance(x, bool)

    def _reset_run_state(self) -> None:
        self._steps = 0
        self._spot_steps = 0
        self._p_ewma = 0.5
        self._last_has_spot = None
        self._tf_transitions = 0
        self._true_steps_for_hazard = 0
        self._avail_streak = 0
        self._unavail_streak = 0

        self._run_type = None
        self._run_len = 0

        self._od_debt = 0.0
        self._od_lock = False

        self._commit_type = None
        self._commit_remaining = 0
        self._overhead_steps = 1

        self._tdt_cache_len = 0
        self._tdt_cache_done = 0.0
        self._tdt_cache_kind = "unknown"

    def _maybe_reset_episode(self) -> None:
        elapsed_raw = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        if self._prev_elapsed_raw is None or elapsed_raw + 1e-12 < self._prev_elapsed_raw:
            self._reset_run_state()

            gap_raw = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
            deadline_raw = float(getattr(self, "deadline", 0.0) or 0.0)
            task_raw = float(getattr(self, "task_duration", 0.0) or 0.0)

            # Heuristic unit normalization: if values look like hours (gap < 5, horizon < 200)
            if gap_raw < 5.0 and max(deadline_raw, task_raw) <= 200.0:
                self._time_scale = 3600.0
            else:
                self._time_scale = 1.0

            overhead_raw = float(getattr(self, "restart_overhead", 0.0) or 0.0)
            overhead = overhead_raw * self._time_scale
            gap = gap_raw * self._time_scale
            if gap <= 1e-9:
                self._overhead_steps = 1
            else:
                self._overhead_steps = max(1, int(math.ceil(max(0.0, overhead) / gap)))

        self._prev_elapsed_raw = elapsed_raw

    def _seg_to_duration(self, seg: Any) -> float:
        if seg is None:
            return 0.0
        if self._is_number(seg):
            return float(seg)
        if isinstance(seg, (tuple, list)) and len(seg) >= 2 and self._is_number(seg[0]) and self._is_number(seg[1]):
            return max(0.0, float(seg[1]) - float(seg[0]))
        if isinstance(seg, dict):
            if "duration" in seg and self._is_number(seg["duration"]):
                return max(0.0, float(seg["duration"]))
            if "start" in seg and "end" in seg and self._is_number(seg["start"]) and self._is_number(seg["end"]):
                return max(0.0, float(seg["end"]) - float(seg["start"]))
        return 0.0

    def _work_done_raw(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0
        if self._is_number(tdt):
            return max(0.0, float(tdt))

        if isinstance(tdt, list):
            n = len(tdt)
            if n == 0:
                self._tdt_cache_len = 0
                self._tdt_cache_done = 0.0
                self._tdt_cache_kind = "unknown"
                return 0.0

            # Detect if it's a list of numbers
            all_nums = all(self._is_number(x) for x in tdt)
            if all_nums:
                # Check if it looks cumulative (non-decreasing)
                k = min(n - 1, 10)
                nondecreasing = True
                for i in range(n - k, n - 1):
                    if float(tdt[i]) > float(tdt[i + 1]) + 1e-12:
                        nondecreasing = False
                        break
                if nondecreasing:
                    self._tdt_cache_kind = "cumulative"
                    return max(0.0, float(tdt[-1]))
                # Otherwise treat as increments
                if self._tdt_cache_kind != "increments":
                    self._tdt_cache_kind = "increments"
                    self._tdt_cache_len = 0
                    self._tdt_cache_done = 0.0
                if n < self._tdt_cache_len:
                    self._tdt_cache_len = 0
                    self._tdt_cache_done = 0.0
                for x in tdt[self._tdt_cache_len :]:
                    self._tdt_cache_done += max(0.0, float(x))
                self._tdt_cache_len = n
                return self._tdt_cache_done

            # Segments or mixed; assume append-only segments
            if self._tdt_cache_kind != "segments":
                self._tdt_cache_kind = "segments"
                self._tdt_cache_len = 0
                self._tdt_cache_done = 0.0
            if n < self._tdt_cache_len:
                self._tdt_cache_len = 0
                self._tdt_cache_done = 0.0
            for seg in tdt[self._tdt_cache_len :]:
                self._tdt_cache_done += self._seg_to_duration(seg)
            self._tdt_cache_len = n
            return max(0.0, self._tdt_cache_done)

        return 0.0

    def _update_stats(self, has_spot: bool) -> None:
        self._steps += 1
        if has_spot:
            self._spot_steps += 1

        x = 1.0 if has_spot else 0.0
        self._p_ewma = (1.0 - self._p_ewma_alpha) * self._p_ewma + self._p_ewma_alpha * x

        if self._last_has_spot is True:
            self._true_steps_for_hazard += 1
            if not has_spot:
                self._tf_transitions += 1

        if has_spot:
            self._avail_streak = self._avail_streak + 1
            self._unavail_streak = 0
        else:
            self._unavail_streak = self._unavail_streak + 1
            self._avail_streak = 0

        self._last_has_spot = has_spot

    def _update_run_streak(self, last_cluster_type: ClusterType) -> None:
        if self._run_type is None:
            self._run_type = last_cluster_type
            self._run_len = 1
            return
        if last_cluster_type == self._run_type:
            self._run_len += 1
        else:
            self._run_type = last_cluster_type
            self._run_len = 1

    def _maybe_force_commitment(self, has_spot: bool) -> Optional[ClusterType]:
        if self._od_lock and self._commit_type is not None and self._commit_type != ClusterType.ON_DEMAND:
            self._commit_type = None
            self._commit_remaining = 0

        if self._commit_remaining <= 0 or self._commit_type is None:
            return None

        if self._commit_type == ClusterType.ON_DEMAND:
            self._commit_remaining -= 1
            return ClusterType.ON_DEMAND

        if self._commit_type == ClusterType.SPOT:
            if has_spot:
                self._commit_remaining -= 1
                return ClusterType.SPOT
            self._commit_type = None
            self._commit_remaining = 0
            return None

        self._commit_type = None
        self._commit_remaining = 0
        return None

    def _set_commitment_if_switch(self, last_cluster_type: ClusterType, new_type: ClusterType) -> None:
        if new_type in (ClusterType.SPOT, ClusterType.ON_DEMAND) and new_type != last_cluster_type:
            self._commit_type = new_type
            self._commit_remaining = max(0, self._overhead_steps)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._maybe_reset_episode()
        self._update_stats(has_spot)
        self._update_run_streak(last_cluster_type)

        forced = self._maybe_force_commitment(has_spot)
        if forced is not None:
            return forced

        scale = self._time_scale
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0) * scale
        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0) * scale

        deadline = float(getattr(self, "deadline", 0.0) or 0.0) * scale
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0) * scale
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0) * scale

        done = self._work_done_raw() * scale
        remaining = max(0.0, task_duration - done)
        if remaining <= 1e-9:
            return ClusterType.NONE

        time_left = max(0.0, deadline - elapsed)
        if time_left <= 1e-9:
            return ClusterType.ON_DEMAND

        # Spot availability probability estimate (smoothed + EWMA)
        alpha = 3.0
        p_long = (self._spot_steps + alpha) / (self._steps + 2.0 * alpha)
        p = 0.35 * p_long + 0.65 * self._p_ewma
        p = min(0.995, max(0.005, p))

        # Hazard of losing spot between steps (based on observed True->False transitions)
        hazard = (self._tf_transitions + 1.0) / (self._true_steps_for_hazard + 2.0)
        hazard = min(1.0, max(0.0, hazard))

        # Expected future overhead time due to spot interruptions if we keep using spot when available
        expected_spot_steps_remaining = (p * time_left) / max(gap, 1e-9)
        expected_preemptions = hazard * expected_spot_steps_remaining
        expected_overhead = expected_preemptions * overhead

        safe_remaining = remaining + expected_overhead + overhead  # add one extra restart for safety
        slack = time_left - safe_remaining

        # Trigger OD lock near deadline (keep running OD to avoid interruption risk)
        if not self._od_lock:
            if time_left <= remaining + 6.0 * overhead + 2.0 * gap:
                self._od_lock = True
            elif slack <= max(0.0, 2.0 * overhead):
                self._od_lock = True

        # Hard deadline safety: if too tight, run OD regardless
        if time_left <= remaining + 2.0 * overhead + gap:
            if not self._od_lock:
                self._od_lock = True
            self._set_commitment_if_switch(last_cluster_type, ClusterType.ON_DEMAND)
            return ClusterType.ON_DEMAND

        if self._od_lock:
            self._set_commitment_if_switch(last_cluster_type, ClusterType.ON_DEMAND)
            return ClusterType.ON_DEMAND

        # Required average work rate from now to finish
        r = safe_remaining / max(time_left, 1e-9)
        r = min(2.0, max(0.0, r))

        # Fraction of non-spot time we should cover with OD to meet expected rate
        denom = max(1e-6, 1.0 - p)
        f_od_when_no_spot = (r - p) / denom
        if f_od_when_no_spot < 0.0:
            f_od_when_no_spot = 0.0
        elif f_od_when_no_spot > 1.0:
            f_od_when_no_spot = 1.0

        # Cap OD debt by expected deficit (avoid over-accumulating)
        expected_spot_work = max(0.0, p * time_left - expected_overhead)
        max_od_needed = max(0.0, safe_remaining - expected_spot_work)
        if self._od_debt > max_od_needed:
            self._od_debt = max_od_needed

        # Decision
        decision: ClusterType

        if has_spot:
            # If currently on OD, avoid switching to a very brief spot window.
            if last_cluster_type == ClusterType.ON_DEMAND:
                # Switch to spot if the window seems stable, else wait 1 step.
                if self._avail_streak >= 2 or p >= 0.55:
                    decision = ClusterType.SPOT
                else:
                    decision = ClusterType.ON_DEMAND
            else:
                decision = ClusterType.SPOT

            # Slightly decay debt during spot time (conditions improved)
            self._od_debt *= 0.98

        else:
            # If we are already on OD, keep it for a minimum run to reduce thrash.
            min_od_run = max(1, self._overhead_steps)
            if last_cluster_type == ClusterType.ON_DEMAND and self._run_len < min_od_run:
                decision = ClusterType.ON_DEMAND
            else:
                # Update debt and decide OD vs NONE during no-spot time
                debt_if_none = self._od_debt + f_od_when_no_spot * gap
                # If slack is getting smaller, be more aggressive.
                threshold = 0.5 * gap
                if slack <= 2.0 * 3600.0:  # 2 hours, in seconds scale (or scaled from hours)
                    threshold = 0.2 * gap

                if debt_if_none >= threshold:
                    decision = ClusterType.ON_DEMAND
                    self._od_debt = max(0.0, debt_if_none - gap)
                else:
                    decision = ClusterType.NONE
                    self._od_debt = debt_if_none

        # Enforce API constraint
        if decision == ClusterType.SPOT and not has_spot:
            decision = ClusterType.ON_DEMAND

        self._set_commitment_if_switch(last_cluster_type, decision)
        return decision

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)