import math
from typing import Optional, Any

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:  # pragma: no cover
    from enum import Enum

    class ClusterType(Enum):
        SPOT = "spot"
        ON_DEMAND = "on_demand"
        NONE = "none"

    class Strategy:  # minimal stub
        def __init__(self, *args, **kwargs):
            self.env = type("Env", (), {"elapsed_seconds": 0, "gap_seconds": 60, "cluster_type": ClusterType.NONE})()
            self.task_duration = 0
            self.task_done_time = []
            self.deadline = 0
            self.restart_overhead = 0


class Solution(Strategy):
    NAME = "slack_aware_hysteresis_v1"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args

        self._last_elapsed: Optional[float] = None
        self._running_type: ClusterType = ClusterType.NONE
        self._overhead_remain: float = 0.0
        self._done_est: float = 0.0

        self._prev_has_spot: Optional[bool] = None
        self._current_avail_run_steps: int = 0
        self._consec_spot_avail: int = 0

        self._ema_up: Optional[float] = None
        self._ema_down: Optional[float] = None
        self._ema_alpha: float = 0.25

        self._committed_od: bool = False
        self._total_slack: Optional[float] = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _parse_done_seconds(self) -> Optional[float]:
        if not hasattr(self, "task_done_time"):
            return None
        tdt = self.task_done_time
        if tdt is None or len(tdt) == 0:
            return None

        try:
            if all(
                isinstance(x, (tuple, list))
                and len(x) == 2
                and isinstance(x[0], (int, float))
                and isinstance(x[1], (int, float))
                for x in tdt
            ):
                return float(sum(max(0.0, float(x[1]) - float(x[0])) for x in tdt))
        except Exception:
            pass

        try:
            if all(isinstance(x, dict) for x in tdt):
                total = 0.0
                ok = False
                for d in tdt:
                    if "start" in d and "end" in d:
                        total += max(0.0, float(d["end"]) - float(d["start"]))
                        ok = True
                    elif "duration" in d:
                        total += max(0.0, float(d["duration"]))
                        ok = True
                return total if ok else None
        except Exception:
            pass

        try:
            if all(isinstance(x, (int, float)) for x in tdt):
                total = float(sum(float(x) for x in tdt))
                last = float(tdt[-1])
                td = None
                try:
                    td = float(self.task_duration)
                except Exception:
                    td = None

                if td and td > 0:
                    if total <= td * 1.10:
                        return total
                    if last <= td * 1.10 and total > td * 1.50:
                        return last

                if last <= 0:
                    return total
                return total if total <= last * 1.20 else last
        except Exception:
            pass

        try:
            total = 0.0
            ok = False
            for x in tdt:
                if hasattr(x, "duration"):
                    total += float(getattr(x, "duration"))
                    ok = True
                elif hasattr(x, "start_time") and hasattr(x, "end_time"):
                    total += max(0.0, float(getattr(x, "end_time")) - float(getattr(x, "start_time")))
                    ok = True
            return total if ok else None
        except Exception:
            return None

    def _update_availability_stats(self, has_spot: bool, gap: float) -> None:
        if self._prev_has_spot is None:
            self._prev_has_spot = has_spot
            self._current_avail_run_steps = 1
            self._consec_spot_avail = 1 if has_spot else 0
            if self._ema_up is None:
                self._ema_up = 3.0 * 3600.0
            if self._ema_down is None:
                self._ema_down = 15.0 * 60.0
            return

        if has_spot:
            self._consec_spot_avail += 1
        else:
            self._consec_spot_avail = 0

        if self._prev_has_spot == has_spot:
            self._current_avail_run_steps += 1
            self._prev_has_spot = has_spot
            return

        dur = float(self._current_avail_run_steps) * gap
        a = self._ema_alpha

        if self._prev_has_spot and (not has_spot):
            # ended an "up" run
            if self._ema_up is None:
                self._ema_up = dur
            else:
                self._ema_up = (1.0 - a) * self._ema_up + a * dur
        elif (not self._prev_has_spot) and has_spot:
            # ended a "down" run
            if self._ema_down is None:
                self._ema_down = dur
            else:
                self._ema_down = (1.0 - a) * self._ema_down + a * dur

        self._prev_has_spot = has_spot
        self._current_avail_run_steps = 1

    def _simulate_progress_for_last_step(self, current_has_spot: bool, gap: float) -> None:
        if self._last_elapsed is None:
            return

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        dt = elapsed - float(self._last_elapsed)
        if not (dt > 0.0):
            dt = float(gap)

        # Work occurs only if we were running an instance during last step.
        if self._running_type in (ClusterType.SPOT, ClusterType.ON_DEMAND):
            if self._running_type == ClusterType.SPOT and self._prev_has_spot is False:
                # Should not happen; be conservative.
                dt_work = 0.0
            else:
                if self._overhead_remain > 0.0:
                    consumed = min(self._overhead_remain, dt)
                    self._overhead_remain -= consumed
                    dt_work = dt - consumed
                else:
                    dt_work = dt
            if dt_work > 0.0:
                self._done_est += dt_work

        # Spot preemption at the boundary into this step.
        if self._running_type == ClusterType.SPOT and self._prev_has_spot is True and current_has_spot is False:
            self._running_type = ClusterType.NONE
            self._overhead_remain = 0.0

        try:
            td = float(self.task_duration)
            if self._done_est > td:
                self._done_est = td
        except Exception:
            pass

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        gap = float(getattr(self.env, "gap_seconds", 60.0))
        ro = float(getattr(self, "restart_overhead", 0.0))

        if self._last_elapsed is None and last_cluster_type is not None:
            self._running_type = last_cluster_type

        # Update progress model for last step (uses previous has_spot stored before updating stats).
        self._simulate_progress_for_last_step(has_spot, gap)

        # Update spot availability stats based on current has_spot.
        self._update_availability_stats(has_spot, gap)

        # Determine done/remaining.
        done_true = self._parse_done_seconds()
        done = done_true if done_true is not None else self._done_est

        try:
            td = float(self.task_duration)
        except Exception:
            td = 0.0
        if td > 0.0:
            done = max(0.0, min(done, td))
        remaining = max(0.0, td - done)

        if remaining <= 0.0:
            self._running_type = ClusterType.NONE
            self._overhead_remain = 0.0
            self._last_elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
            return ClusterType.NONE

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        try:
            deadline = float(self.deadline)
        except Exception:
            deadline = elapsed + remaining + 1.0
        time_left = deadline - elapsed

        if self._total_slack is None:
            self._total_slack = max(0.0, deadline - td) if td > 0.0 else 0.0

        slack_remaining = time_left - remaining
        urgent_buffer = max(2.0 * ro, 2.0 * gap)
        commit_buffer = max(4.0 * ro, 4.0 * gap)

        # Force on-demand if we are too close to the deadline.
        if (not self._committed_od) and (time_left <= remaining + urgent_buffer):
            self._committed_od = True
        if (not self._committed_od) and (slack_remaining <= commit_buffer):
            self._committed_od = True

        if self._committed_od:
            action = ClusterType.ON_DEMAND
        else:
            if has_spot:
                if self._running_type == ClusterType.SPOT:
                    action = ClusterType.SPOT
                else:
                    ema_up = self._ema_up if self._ema_up is not None else 3.0 * 3600.0
                    min_consec = 2
                    min_uptime = max(2.0 * ro, 3.0 * gap)
                    big_slack = max(2.0 * 3600.0, 0.25 * (self._total_slack or 0.0), 0.0)
                    stable = ema_up >= min_uptime

                    if self._consec_spot_avail >= min_consec and (stable or slack_remaining >= big_slack):
                        action = ClusterType.SPOT
                    else:
                        action = ClusterType.ON_DEMAND
            else:
                if self._running_type == ClusterType.ON_DEMAND:
                    action = ClusterType.ON_DEMAND
                else:
                    ema_down = self._ema_down if self._ema_down is not None else 20.0 * 60.0
                    expected_wait = min(max(ema_down, gap), 2.0 * 3600.0)
                    wait_margin = expected_wait + urgent_buffer

                    # Use slack to wait through outages if they are expected to be short.
                    if slack_remaining > wait_margin and expected_wait <= 3600.0 and remaining > 3600.0:
                        action = ClusterType.NONE
                    else:
                        action = ClusterType.ON_DEMAND

        # Enforce "no spot when unavailable"
        if action == ClusterType.SPOT and (not has_spot):
            action = ClusterType.ON_DEMAND

        # Apply launch overhead model.
        if action in (ClusterType.SPOT, ClusterType.ON_DEMAND):
            if self._running_type != action:
                self._overhead_remain = ro
            self._running_type = action
        else:
            self._running_type = ClusterType.NONE
            self._overhead_remain = 0.0

        self._last_elapsed = elapsed
        return action

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)