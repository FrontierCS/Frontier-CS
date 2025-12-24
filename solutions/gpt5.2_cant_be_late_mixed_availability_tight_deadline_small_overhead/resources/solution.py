import math
from collections import deque

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass
        self._inited = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

    def _init_state(self):
        self._inited = True

        self._p_spot = 0.5
        self._p_alpha = 0.02

        self._last_has_spot = None
        self._up_streak_s = 0.0
        self._down_streak_s = 0.0
        self._avg_up_s = None
        self._avg_down_s = None
        self._len_alpha = 0.2

        self._hist = deque(maxlen=1)

        self._commit_od = False
        self._last_choice = None
        self._last_switch_t = -1e18
        self._overhead_until = -1e18

    def _work_done_seconds(self):
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return 0.0

        # If list of (start, end) segments:
        last = tdt[-1]
        if isinstance(last, (tuple, list)) and len(last) >= 2:
            s = 0.0
            for seg in tdt:
                if isinstance(seg, (tuple, list)) and len(seg) >= 2:
                    try:
                        s += float(seg[1]) - float(seg[0])
                    except Exception:
                        pass
            return max(0.0, s)

        # If numeric list: either cumulative or increments
        try:
            nums = [float(x) for x in tdt]
        except Exception:
            # Fallback: try last numeric
            try:
                return float(last)
            except Exception:
                return 0.0

        if not nums:
            return 0.0

        monotone = True
        for i in range(len(nums) - 1):
            if nums[i + 1] + 1e-9 < nums[i]:
                monotone = False
                break

        s = sum(nums)
        lastv = nums[-1]

        # Heuristics:
        # - cumulative tends to be monotone and sum far larger than last.
        # - increments may be non-monotone; sum close to task_duration.
        td = float(getattr(self, "task_duration", 0.0) or 0.0)
        if monotone:
            if td > 0 and s > min(td * 3.0, td + 3600.0):
                return max(0.0, min(lastv, td if td > 0 else lastv))
            if len(nums) >= 2 and (s > lastv * 1.5):
                return max(0.0, lastv)
            # ambiguous: prefer last if it looks like cumulative
            if td > 0 and lastv <= td and abs(s - lastv) < 1e-6:
                return max(0.0, lastv)

        # default to sum of segments
        if td > 0:
            return max(0.0, min(s, td))
        return max(0.0, s)

    def _update_availability_stats(self, has_spot: bool):
        t = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)

        # EMA probability
        x = 1.0 if has_spot else 0.0
        self._p_spot = (1.0 - self._p_alpha) * self._p_spot + self._p_alpha * x

        # window history
        win_seconds = 3600.0
        maxlen = max(1, int(win_seconds / max(gap, 1e-9)))
        if self._hist.maxlen != maxlen:
            old = list(self._hist)
            self._hist = deque(old[-maxlen:], maxlen=maxlen)
        self._hist.append(1 if has_spot else 0)

        # streaks and avg lengths
        if self._last_has_spot is None:
            self._last_has_spot = has_spot
            if has_spot:
                self._up_streak_s = gap
                self._down_streak_s = 0.0
            else:
                self._down_streak_s = gap
                self._up_streak_s = 0.0
            return

        if has_spot == self._last_has_spot:
            if has_spot:
                self._up_streak_s += gap
            else:
                self._down_streak_s += gap
        else:
            # transition: update averages for the streak that ended
            if self._last_has_spot:
                ended = self._up_streak_s
                if ended > 0:
                    if self._avg_up_s is None:
                        self._avg_up_s = ended
                    else:
                        self._avg_up_s = (1.0 - self._len_alpha) * self._avg_up_s + self._len_alpha * ended
                self._up_streak_s = 0.0
                self._down_streak_s = gap
            else:
                ended = self._down_streak_s
                if ended > 0:
                    if self._avg_down_s is None:
                        self._avg_down_s = ended
                    else:
                        self._avg_down_s = (1.0 - self._len_alpha) * self._avg_down_s + self._len_alpha * ended
                self._down_streak_s = 0.0
                self._up_streak_s = gap

            self._last_has_spot = has_spot

    def _spot_window_fraction(self):
        if not self._hist:
            return self._p_spot
        return sum(self._hist) / float(len(self._hist))

    def _estimate_wait_for_spot(self):
        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)

        # If we have avg downtime, use remaining expected downtime
        if self._avg_down_s is not None and self._down_streak_s > 0.0:
            return max(0.0, self._avg_down_s - self._down_streak_s)

        # Otherwise, use geometric estimate based on p_spot and observed window
        p = max(1e-6, min(1.0, 0.5 * self._p_spot + 0.5 * self._spot_window_fraction()))
        # expected steps until available from now ~ 1/p
        return gap * (1.0 / p)

    def _maybe_set_commit_od(self, remaining_work_s: float, time_left_s: float):
        if self._commit_od:
            return
        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        # Conservative: if running OD from now with a single (possible) restart overhead cannot miss deadline
        # Add a small discretization buffer.
        buffer_s = 2.0 * gap
        safe_need = remaining_work_s + ro + buffer_s
        if time_left_s <= safe_need:
            self._commit_od = True

    def _switch_allowed(self, now_s: float):
        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        # Avoid switching while in overhead; also impose a cooldown.
        if now_s < self._overhead_until - 1e-9:
            return False
        cooldown_s = max(1800.0, 10.0 * gap, 2.0 * ro)
        return (now_s - self._last_switch_t) >= cooldown_s

    def _record_choice(self, last_cluster_type: ClusterType, choice: ClusterType):
        now_s = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        if choice != last_cluster_type:
            self._last_switch_t = now_s
            if choice != ClusterType.NONE:
                self._overhead_until = now_s + ro

        self._last_choice = choice

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._inited:
            self._init_state()

        self._update_availability_stats(has_spot)

        now_s = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        td = float(getattr(self, "task_duration", 0.0) or 0.0)

        done_s = self._work_done_seconds()
        remaining_work_s = max(0.0, td - done_s)
        if remaining_work_s <= 1e-6:
            choice = ClusterType.NONE
            self._record_choice(last_cluster_type, choice)
            return choice

        time_left_s = max(0.0, deadline - now_s)
        slack_s = time_left_s - remaining_work_s

        self._maybe_set_commit_od(remaining_work_s, time_left_s)
        if self._commit_od:
            choice = ClusterType.ON_DEMAND
            self._record_choice(last_cluster_type, choice)
            return choice

        # If we're extremely close, be safe
        if slack_s <= max(2.0 * gap, ro + gap):
            choice = ClusterType.ON_DEMAND if (has_spot is False) else ClusterType.ON_DEMAND
            self._record_choice(last_cluster_type, choice)
            return choice

        switch_ok = self._switch_allowed(now_s)

        if not has_spot:
            # Decide whether to wait for spot or run on-demand
            exp_wait = self._estimate_wait_for_spot()
            buffer_s = max(2.0 * gap, 600.0)  # 10 min
            # Require enough slack to cover waiting + one restart overhead + buffer
            if slack_s >= (exp_wait + ro + buffer_s):
                choice = ClusterType.NONE
            else:
                choice = ClusterType.ON_DEMAND
            self._record_choice(last_cluster_type, choice)
            return choice

        # has_spot == True
        if last_cluster_type == ClusterType.SPOT:
            choice = ClusterType.SPOT
            self._record_choice(last_cluster_type, choice)
            return choice

        if last_cluster_type == ClusterType.NONE:
            choice = ClusterType.SPOT
            self._record_choice(last_cluster_type, choice)
            return choice

        # last_cluster_type == ON_DEMAND
        # Consider switching back to spot if it seems stable and enough work remains to justify overhead.
        spot_frac = self._spot_window_fraction()
        min_work_for_switch = max(2.0 * 3600.0, 20.0 * ro, 12.0 * gap)  # at least 2h remaining
        min_slack_for_switch = max(3600.0, 8.0 * ro, 6.0 * gap)  # at least 1h slack
        stable_enough = (spot_frac >= 0.6 and self._p_spot >= 0.55)

        if switch_ok and stable_enough and remaining_work_s >= min_work_for_switch and slack_s >= min_slack_for_switch:
            choice = ClusterType.SPOT
        else:
            choice = ClusterType.ON_DEMAND

        self._record_choice(last_cluster_type, choice)
        return choice
