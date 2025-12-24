import math
from collections import deque
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_adaptive_v1"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self._initialized = False

        self._spot_hist = None  # type: Optional[deque]
        self._absent_od_hist = None  # type: Optional[deque]

        self._prev_has_spot = None  # type: Optional[bool]

        self._run_time_selected = 0.0
        self._od_lock_steps = 0
        self._consec_spot = 0
        self._consec_nospot = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _clamp(x: float, lo: float, hi: float) -> float:
        if x < lo:
            return lo
        if x > hi:
            return hi
        return x

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        gap = max(gap, 1.0)

        # Rolling window sizes (in steps) based on gap
        # spot window ~ 6 hours, absent-OD window ~ 3 hours, with sane caps
        spot_w = int(self._clamp(round(6.0 * 3600.0 / gap), 120, 4000))
        absent_w = int(self._clamp(round(3.0 * 3600.0 / gap), 60, 2500))

        self._spot_hist = deque(maxlen=spot_w)
        self._absent_od_hist = deque(maxlen=absent_w)
        self._initialized = True

    def _extract_done_work_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        task_dur = float(getattr(self, "task_duration", 0.0) or 0.0)

        done = 0.0
        if td is None:
            done = 0.0
        elif isinstance(td, (int, float)):
            done = float(td)
        elif isinstance(td, list):
            if not td:
                done = 0.0
            else:
                try:
                    first = td[0]
                    if isinstance(first, (tuple, list)) and len(first) == 2:
                        s = 0.0
                        for a, b in td:
                            try:
                                aa = float(a)
                                bb = float(b)
                                if bb > aa:
                                    s += (bb - aa)
                            except Exception:
                                continue
                        done = s
                    else:
                        vals = []
                        for x in td:
                            try:
                                vals.append(float(x))
                            except Exception:
                                continue
                        if not vals:
                            done = 0.0
                        else:
                            s = sum(vals)
                            last = vals[-1]
                            # If values look cumulative, sum will dwarf last.
                            if last > 0 and s > last * 1.25:
                                done = last
                            else:
                                done = s
                except Exception:
                    done = 0.0
        else:
            try:
                done = float(td)
            except Exception:
                done = 0.0

        if task_dur > 0:
            done = self._clamp(done, 0.0, task_dur)
        else:
            done = max(0.0, done)

        # Never assume we did more work than time we selected to run (conservative bound).
        done = min(done, self._run_time_selected)

        # Small safety buffer to avoid overestimating progress (covers overhead/measurement quirks).
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        done = max(0.0, done - 2.0 * ro)

        return done

    def _calc_od_lock_steps(self) -> int:
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        # Keep OD at least ~30 minutes, but scale with overhead and step size.
        lock_seconds = max(1800.0, 8.0 * ro, 3.0 * gap)
        return max(0, int(math.ceil(lock_seconds / max(gap, 1.0))))

    def _update_stats_from_previous_step(self, last_cluster_type: ClusterType, has_spot: bool) -> None:
        self._ensure_initialized()

        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        gap = max(gap, 1.0)

        # Update selected run-time using the cluster type that actually ran in the previous step.
        if last_cluster_type != ClusterType.NONE:
            self._run_time_selected += gap

        # Update absent/OD ratio based on previous step's spot availability.
        if self._prev_has_spot is not None and self._prev_has_spot is False:
            self._absent_od_hist.append(1 if last_cluster_type == ClusterType.ON_DEMAND else 0)

        # Update spot availability history for current step (to be used for decision).
        self._spot_hist.append(1 if has_spot else 0)

        if has_spot:
            self._consec_spot += 1
            self._consec_nospot = 0
        else:
            self._consec_nospot += 1
            self._consec_spot = 0

        self._prev_has_spot = has_spot

        if self._od_lock_steps > 0 and last_cluster_type == ClusterType.ON_DEMAND:
            self._od_lock_steps -= 1
        elif last_cluster_type != ClusterType.ON_DEMAND:
            self._od_lock_steps = 0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_stats_from_previous_step(last_cluster_type, has_spot)

        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        gap = max(gap, 1.0)

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_dur = float(getattr(self, "task_duration", 0.0) or 0.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        done = self._extract_done_work_seconds()
        remaining_work = max(0.0, task_dur - done)
        remaining_time = max(0.0, deadline - elapsed)
        slack = remaining_time - remaining_work

        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Hard-urgency: if we're too close, commit to OD (avoid waiting and avoid restart risk).
        if remaining_time <= 0.0:
            return ClusterType.ON_DEMAND
        if remaining_time <= remaining_work + max(4.0 * ro, 2.0 * gap):
            return ClusterType.ON_DEMAND

        # Slack-based critical zone: always OD when slack is small.
        slack_total = max(0.0, deadline - task_dur)
        critical_slack = max(3600.0, 0.08 * slack_total, 12.0 * ro, 3.0 * gap)
        if slack <= critical_slack:
            return ClusterType.ON_DEMAND

        # Default: prefer SPOT whenever it exists (unless we're in an OD lock).
        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND and self._od_lock_steps > 0:
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # No spot available: choose between waiting (NONE) and OD based on how much OD we need.
        # Estimate spot availability rate from recent history.
        if self._spot_hist and len(self._spot_hist) >= 20:
            p = sum(self._spot_hist) / float(len(self._spot_hist))
        else:
            p = 0.25

        p = self._clamp(p, 0.0, 0.95)

        required_rate = remaining_work / max(remaining_time, 1e-9)
        if required_rate >= 0.98:
            # Need near-continuous progress: OD.
            if last_cluster_type != ClusterType.ON_DEMAND:
                self._od_lock_steps = self._calc_od_lock_steps()
            return ClusterType.ON_DEMAND

        # If spot alone (when available) is likely sufficient, we can wait during outages.
        if required_rate <= p * 0.98:
            return ClusterType.NONE

        # Otherwise we need OD for a fraction of the spot-unavailable time.
        # r = fraction of no-spot time to run on-demand to meet required average rate.
        denom = max(1.0 - p, 1e-6)
        r = self._clamp((required_rate - p) / denom, 0.0, 1.0)

        if self._absent_od_hist and len(self._absent_od_hist) >= 10:
            current_r = sum(self._absent_od_hist) / float(len(self._absent_od_hist))
        else:
            current_r = 0.0

        # Extra: if slack is plentiful, allow a short initial wait in an outage even if r>0.
        # This reduces thrash cost and can capture quick spot returns.
        # But don't do it for long outages.
        outage_wait_budget = max(0.0, slack - critical_slack)
        max_wait_steps = int(self._clamp(math.floor(min(outage_wait_budget, 1800.0) / gap), 0, 12))
        if self._consec_nospot <= max_wait_steps and slack > critical_slack + 900.0 and r < 0.9:
            if current_r >= r:
                return ClusterType.NONE

        choose_od = current_r < r

        if choose_od:
            if last_cluster_type != ClusterType.ON_DEMAND:
                self._od_lock_steps = self._calc_od_lock_steps()
            return ClusterType.ON_DEMAND
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
