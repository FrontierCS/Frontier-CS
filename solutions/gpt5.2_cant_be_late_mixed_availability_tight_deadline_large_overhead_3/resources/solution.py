import math
from collections import deque

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


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

        self._initialized = False

        self._forced_od = False
        self._blacklist_spot = False

        self._last_has_spot = None
        self._spot_streak = 0
        self._down_streak = 0

        self._prev_decision = None
        self._od_until = 0.0

        self._spot_segment_start = None
        self._spot_segment_durations = deque(maxlen=8)

        self._preemption_times = deque(maxlen=200)
        self._preemptions = 0

        self._spot_run_seconds = 0.0
        self._od_run_seconds = 0.0

        self._U_ema = None
        self._D_ema = None
        self._cur_up_len = 0.0
        self._cur_down_len = 0.0

        self._done_mode = "unknown"
        self._done_cache = 0.0
        self._done_cache_key = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _is_num(x):
        return isinstance(x, (int, float)) and not isinstance(x, bool)

    def _compute_done_seconds(self) -> float:
        # Prefer any direct attributes if available.
        for attr in ("task_done_seconds", "done_seconds", "completed_seconds"):
            if hasattr(self, attr):
                v = getattr(self, attr)
                if self._is_num(v):
                    return float(v)
        if hasattr(self, "env"):
            for attr in ("task_done_seconds", "done_seconds", "completed_seconds"):
                if hasattr(self.env, attr):
                    v = getattr(self.env, attr)
                    if self._is_num(v):
                        return float(v)

        lst = getattr(self, "task_done_time", None)
        if not lst:
            return 0.0

        # If list identity and length unchanged, use cached.
        cache_key = (id(lst), len(lst))
        if self._done_cache_key == cache_key and self._done_mode != "unknown":
            if self._done_mode == "scalar_last":
                try:
                    return float(lst[-1]) if lst else 0.0
                except Exception:
                    return self._done_cache
            return self._done_cache

        # Detect and compute.
        done = 0.0
        try:
            if all(self._is_num(x) for x in lst):
                # Heuristic: if non-decreasing and bounded by task duration, interpret as cumulative.
                nondec = True
                for i in range(len(lst) - 1):
                    if lst[i] > lst[i + 1]:
                        nondec = False
                        break
                td = float(getattr(self, "task_duration", 0.0) or 0.0)
                if nondec and len(lst) >= 2 and td > 0 and float(lst[-1]) <= td * 1.10:
                    done = float(lst[-1])
                    self._done_mode = "scalar_last"
                else:
                    done = float(sum(float(x) for x in lst))
                    self._done_mode = "scalar_sum"
            else:
                # Sum segment durations.
                for seg in lst:
                    if seg is None:
                        continue
                    if self._is_num(seg):
                        done += float(seg)
                        continue
                    if isinstance(seg, (tuple, list)) and len(seg) == 2 and self._is_num(seg[0]) and self._is_num(seg[1]):
                        done += float(seg[1]) - float(seg[0])
                        continue
                    if isinstance(seg, dict):
                        if "duration" in seg and self._is_num(seg["duration"]):
                            done += float(seg["duration"])
                            continue
                        if "start" in seg and "end" in seg and self._is_num(seg["start"]) and self._is_num(seg["end"]):
                            done += float(seg["end"]) - float(seg["start"])
                            continue
                        if "done" in seg and self._is_num(seg["done"]):
                            done += float(seg["done"])
                            continue
                self._done_mode = "segments_sum"
        except Exception:
            # Fallback best effort.
            try:
                done = float(self._done_cache)
            except Exception:
                done = 0.0
            self._done_mode = "unknown"

        if done < 0:
            done = 0.0

        self._done_cache = done
        self._done_cache_key = cache_key
        return done

    def _ensure_initialized(self):
        if self._initialized:
            return
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if gap <= 0:
            gap = 300.0  # fallback
        self._gap = gap

        R = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        self._R = max(0.0, R)

        # Require spot to be continuously available for ~15 minutes before switching from OD->SPOT.
        confirm_seconds = 900.0
        self._confirm_steps = max(2, min(30, int(math.ceil(confirm_seconds / self._gap))))

        # Cooldown after a preemption to avoid immediate flip-flopping (approx 30 minutes).
        self._cooldown_seconds = max(900.0, 2.0 * confirm_seconds)

        # Slack thresholds.
        self._hard_slack = max(3600.0, 4.0 * self._R)  # force OD when slack gets small
        self._switch_slack = max(5400.0, 6.0 * self._R)  # need this much slack to consider OD->SPOT
        self._min_work_to_switch = 4.0 * 3600.0  # don't switch back to spot for small remaining work

        self._U_ema = 2.0 * 3600.0
        self._D_ema = 1.0 * 3600.0
        self._cur_up_len = 0.0
        self._cur_down_len = 0.0

        self._initialized = True

    def _update_availability_stats(self, has_spot: bool):
        gap = self._gap
        if has_spot:
            self._spot_streak += 1
            self._down_streak = 0
        else:
            self._down_streak += 1
            self._spot_streak = 0

        if self._last_has_spot is None:
            self._last_has_spot = has_spot
            self._cur_up_len = gap if has_spot else 0.0
            self._cur_down_len = gap if not has_spot else 0.0
            return

        if has_spot == self._last_has_spot:
            if has_spot:
                self._cur_up_len += gap
            else:
                self._cur_down_len += gap
            return

        # Transition: finalize run length.
        alpha = 0.15
        if self._last_has_spot:
            # up -> down
            if self._cur_up_len <= 0:
                self._cur_up_len = gap
            self._U_ema = (1.0 - alpha) * self._U_ema + alpha * self._cur_up_len
            self._cur_up_len = 0.0
            self._cur_down_len = gap
        else:
            # down -> up
            if self._cur_down_len <= 0:
                self._cur_down_len = gap
            self._D_ema = (1.0 - alpha) * self._D_ema + alpha * self._cur_down_len
            self._cur_down_len = 0.0
            self._cur_up_len = gap

        self._last_has_spot = has_spot

    def _maybe_blacklist_spot(self):
        # Blacklist if spot segments are consistently too short (restart overhead dominates).
        if self._blacklist_spot:
            return
        if len(self._spot_segment_durations) < 4:
            return

        R = self._R
        if R <= 0:
            return

        segs = list(self._spot_segment_durations)
        avg = sum(segs) / len(segs)
        short = sum(1 for d in segs if d < 1.5 * R)

        # If typical spot windows don't cover overhead, stop using spot.
        if avg < 3.0 * R or short >= 2:
            self._blacklist_spot = True
            return

        # Also blacklist if preemption rate is extremely high during spot usage.
        spot_hours = max(self._spot_run_seconds / 3600.0, 0.1)
        preempt_per_hour = self._preemptions / spot_hours
        if preempt_per_hour > 2.0:
            self._blacklist_spot = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_initialized()

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = self._gap
        R = self._R

        # Track usage time by last cluster (previous interval).
        if last_cluster_type == ClusterType.SPOT:
            self._spot_run_seconds += gap
        elif last_cluster_type == ClusterType.ON_DEMAND:
            self._od_run_seconds += gap

        # Update availability stats.
        self._update_availability_stats(bool(has_spot))

        # Handle preemption and close spot segment if needed.
        preempted_now = (last_cluster_type == ClusterType.SPOT and not has_spot)
        if preempted_now:
            self._preemptions += 1
            self._preemption_times.append(elapsed)
            if self._spot_segment_start is not None:
                dur = max(0.0, elapsed - float(self._spot_segment_start))
                self._spot_segment_durations.append(dur)
                self._spot_segment_start = None
            self._od_until = max(self._od_until, elapsed + self._cooldown_seconds)

        # Work remaining / slack.
        done = self._compute_done_seconds()
        task_dur = float(getattr(self, "task_duration", 0.0) or 0.0)
        remaining_work = max(0.0, task_dur - done)

        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        time_left = deadline - elapsed
        slack = time_left - remaining_work  # time buffer including future overhead/idle

        if remaining_work <= 0.0:
            return ClusterType.NONE

        # If already late or close to deadline, force on-demand forever.
        if time_left <= 0.0 or slack <= self._hard_slack:
            self._forced_od = True

        # Update blacklist logic based on observed spot segment durations.
        self._maybe_blacklist_spot()

        # Decision logic.
        decision = ClusterType.ON_DEMAND

        if self._forced_od or self._blacklist_spot:
            decision = ClusterType.ON_DEMAND
        else:
            if last_cluster_type == ClusterType.SPOT:
                # Stay on spot if available and we have buffer.
                if has_spot and slack > self._hard_slack:
                    decision = ClusterType.SPOT
                else:
                    decision = ClusterType.ON_DEMAND
                    self._od_until = max(self._od_until, elapsed + self._cooldown_seconds)
            else:
                # Last was OD or NONE.
                if has_spot:
                    # Switch to spot only if spot has been stable, enough slack, enough remaining work,
                    # and expected uptime isn't too tiny relative to restart overhead.
                    U = max(self._U_ema, gap)
                    if (
                        elapsed >= self._od_until
                        and self._spot_streak >= self._confirm_steps
                        and slack > self._switch_slack + R
                        and remaining_work >= self._min_work_to_switch
                        and U >= max(1800.0, 3.0 * R + 2.0 * gap)
                    ):
                        decision = ClusterType.SPOT
                    else:
                        decision = ClusterType.ON_DEMAND
                else:
                    decision = ClusterType.ON_DEMAND

        # Never return SPOT when unavailable.
        if decision == ClusterType.SPOT and not has_spot:
            decision = ClusterType.ON_DEMAND

        # Maintain spot segment start/end tracking based on the *new* decision.
        if last_cluster_type == ClusterType.SPOT and decision != ClusterType.SPOT:
            if self._spot_segment_start is not None:
                dur = max(0.0, elapsed - float(self._spot_segment_start))
                self._spot_segment_durations.append(dur)
                self._spot_segment_start = None

        if decision == ClusterType.SPOT and last_cluster_type != ClusterType.SPOT:
            self._spot_segment_start = elapsed

        self._prev_decision = decision
        return decision

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
