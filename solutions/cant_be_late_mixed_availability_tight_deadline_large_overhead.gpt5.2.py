import argparse
import os
import json
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Optional[argparse.Namespace] = None):
        self.args = args
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass

        self._initialized = False
        self._last_elapsed: Optional[float] = None

        self._p_ema: float = 0.5
        self._mean_uptime: float = 3600.0
        self._mean_outage: float = 1800.0
        self._last_avail: Optional[bool] = None
        self._streak_steps: int = 0

        self._prev_action: Optional[ClusterType] = None
        self._last_start_time: float = -1e18
        self._last_started_cluster: Optional[ClusterType] = None

        self._od_commit_until: float = 0.0
        self._permanent_od: bool = False

        self._task_duration_cached: Optional[float] = None
        self._deadline_cached: Optional[float] = None
        self._restart_overhead_cached: Optional[float] = None
        self._total_slack: float = 0.0

        self._spec: dict[str, Any] = {}
        self._spot_price: Optional[float] = None
        self._od_price: Optional[float] = None

    def solve(self, spec_path: str) -> "Solution":
        self._spec = {}
        self._spot_price = None
        self._od_price = None
        if spec_path and os.path.exists(spec_path):
            try:
                with open(spec_path, "r", encoding="utf-8") as f:
                    txt = f.read()
                try:
                    self._spec = json.loads(txt)
                except Exception:
                    self._spec = {}
                for k in ("spot_price", "spot", "price_spot"):
                    v = self._spec.get(k)
                    if isinstance(v, (int, float)):
                        self._spot_price = float(v)
                        break
                for k in ("on_demand_price", "od_price", "on_demand", "price_on_demand"):
                    v = self._spec.get(k)
                    if isinstance(v, (int, float)):
                        self._od_price = float(v)
                        break
            except Exception:
                self._spec = {}
        return self

    def _reset_episode(self) -> None:
        self._initialized = True
        self._last_elapsed = None

        self._p_ema = 0.5
        self._mean_uptime = 3600.0
        self._mean_outage = 1800.0
        self._last_avail = None
        self._streak_steps = 0

        self._prev_action = None
        self._last_start_time = -1e18
        self._last_started_cluster = None

        self._od_commit_until = 0.0
        self._permanent_od = False

        self._task_duration_cached = None
        self._deadline_cached = None
        self._restart_overhead_cached = None
        self._total_slack = 0.0

    def _get_done_work_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0
        if isinstance(td, (int, float)):
            v = float(td)
            return v if v > 0 else 0.0
        if isinstance(td, (list, tuple)):
            if not td:
                return 0.0
            if all(isinstance(x, (int, float)) for x in td):
                v = float(td[-1])
                return v if v > 0 else 0.0

            total = 0.0
            ok = False
            for seg in td:
                if isinstance(seg, (list, tuple)) and len(seg) == 2 and all(isinstance(y, (int, float)) for y in seg):
                    total += float(seg[1]) - float(seg[0])
                    ok = True
                elif isinstance(seg, dict):
                    if "start" in seg and "end" in seg and isinstance(seg["start"], (int, float)) and isinstance(seg["end"], (int, float)):
                        total += float(seg["end"]) - float(seg["start"])
                        ok = True
                    elif "duration" in seg and isinstance(seg["duration"], (int, float)):
                        total += float(seg["duration"])
                        ok = True
            if ok:
                return total if total > 0 else 0.0
        return 0.0

    def _update_availability_stats(self, has_spot: bool, gap: float) -> None:
        alpha = 0.04
        self._p_ema = (1.0 - alpha) * self._p_ema + alpha * (1.0 if has_spot else 0.0)

        if self._last_avail is None:
            self._last_avail = has_spot
            self._streak_steps = 1
            return

        if has_spot == self._last_avail:
            self._streak_steps += 1
            return

        duration = float(self._streak_steps) * gap
        beta = 0.22
        if self._last_avail:
            self._mean_uptime = (1.0 - beta) * self._mean_uptime + beta * max(duration, gap)
            self._mean_uptime = max(self._mean_uptime, gap)
        else:
            self._mean_outage = (1.0 - beta) * self._mean_outage + beta * max(duration, gap)
            self._mean_outage = max(self._mean_outage, gap)

        self._last_avail = has_spot
        self._streak_steps = 1

    def _note_action_start(self, action: ClusterType, t: float) -> None:
        if action in (ClusterType.SPOT, ClusterType.ON_DEMAND):
            if action != self._prev_action:
                self._last_start_time = t
                self._last_started_cluster = action
        self._prev_action = action

    def _overhead_pending_and_should_hold(self, current_cluster: ClusterType, has_spot: bool, t: float) -> bool:
        if self._last_started_cluster is None:
            return False
        if current_cluster != self._last_started_cluster:
            return False
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        if ro <= 0:
            return False
        if (t - self._last_start_time) < ro:
            if current_cluster == ClusterType.SPOT and not has_spot:
                return False
            return True
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        t = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        if gap <= 0:
            gap = 1.0

        if (not self._initialized) or (self._last_elapsed is not None and t + 1e-9 < self._last_elapsed) or (t == 0.0 and self._last_elapsed not in (None, 0.0)):
            self._reset_episode()

        self._last_elapsed = t

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        if self._task_duration_cached != task_duration or self._deadline_cached != deadline or self._restart_overhead_cached != restart_overhead:
            self._task_duration_cached = task_duration
            self._deadline_cached = deadline
            self._restart_overhead_cached = restart_overhead
            self._total_slack = max(0.0, deadline - task_duration)

        done = self._get_done_work_seconds()
        remaining_work = max(0.0, task_duration - done)
        if remaining_work <= 0.0:
            self._note_action_start(ClusterType.NONE, t)
            return ClusterType.NONE

        self._update_availability_stats(has_spot, gap)

        time_remaining = deadline - t
        if time_remaining <= 0.0:
            self._note_action_start(ClusterType.ON_DEMAND, t)
            return ClusterType.ON_DEMAND

        slack = time_remaining - remaining_work

        current_cluster = last_cluster_type

        if self._overhead_pending_and_should_hold(current_cluster, has_spot, t):
            self._note_action_start(current_cluster, t)
            return current_cluster

        reserve = max(1800.0, 2.5 * restart_overhead, 0.22 * self._total_slack)
        critical = max(900.0, 4.0 * restart_overhead, 0.08 * self._total_slack)

        if slack <= critical:
            self._permanent_od = True

        if self._permanent_od:
            action = ClusterType.ON_DEMAND
            self._note_action_start(action, t)
            return action

        if t < self._od_commit_until:
            action = ClusterType.ON_DEMAND
            self._note_action_start(action, t)
            return action

        mean_cycle = max(gap, self._mean_uptime + self._mean_outage)
        expected_switch_overhead_rate = (2.0 * restart_overhead) / mean_cycle  # seconds overhead per second wall-clock
        allowed_overhead_rate = max(0.0, slack) / max(1.0, time_remaining)

        if remaining_work > 6.0 * 3600.0 and expected_switch_overhead_rate > 0.9 * allowed_overhead_rate and slack < 1.8 * reserve:
            commit = min(6.0 * 3600.0, max(2.0 * 3600.0, 1.2 * self._mean_outage))
            self._od_commit_until = max(self._od_commit_until, t + commit)
            action = ClusterType.ON_DEMAND
            self._note_action_start(action, t)
            return action

        if has_spot:
            final_window = max(2.0 * gap, restart_overhead + 2.0 * gap)
            if remaining_work <= final_window and slack <= reserve:
                action = ClusterType.ON_DEMAND
                self._od_commit_until = max(self._od_commit_until, t + min(2.0 * 3600.0, max(3600.0, self._mean_outage)))
            else:
                action = ClusterType.SPOT
            self._note_action_start(action, t)
            return action

        outage_time = (float(self._streak_steps) * gap) if (self._last_avail is False) else 0.0
        expected_wait = max(gap, self._mean_outage)
        max_wait_chunk = min(2.0 * 3600.0, max(3600.0, 0.45 * self._total_slack))

        if outage_time >= max_wait_chunk:
            commit = min(6.0 * 3600.0, max(3600.0, 1.1 * self._mean_outage))
            self._od_commit_until = max(self._od_commit_until, t + commit)
            action = ClusterType.ON_DEMAND
            self._note_action_start(action, t)
            return action

        if slack > 1.5 * expected_wait + reserve and slack > reserve:
            action = ClusterType.NONE
            self._note_action_start(action, t)
            return action

        commit = min(6.0 * 3600.0, max(3600.0, 1.0 * self._mean_outage))
        self._od_commit_until = max(self._od_commit_until, t + commit)
        action = ClusterType.ON_DEMAND
        self._note_action_start(action, t)
        return action

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
