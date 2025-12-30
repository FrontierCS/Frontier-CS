import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_slack_guard_v1"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self._initialized = False

        self._commit_to_od = False

        self._cooldown_steps = 0

        self._idle_buffer = 0.0
        self._stop_buffer = 0.0
        self._commit_buffer = 0.0
        self._cooldown_on_switch_steps = 0

        self._tdt_id = None
        self._tdt_mode = None  # "cumulative" or "sum"
        self._tdt_sum = 0.0
        self._tdt_len = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        self._idle_buffer = max(3.0 * gap, 4.0 * overhead, 600.0)
        self._stop_buffer = 2.0 * self._idle_buffer
        self._commit_buffer = max(12.0 * gap, 8.0 * overhead, 900.0)

        self._cooldown_on_switch_steps = int(math.ceil(overhead / gap)) if overhead > 0.0 else 0

        self._initialized = True

    @staticmethod
    def _is_number(x: Any) -> bool:
        return isinstance(x, (int, float)) and not isinstance(x, bool)

    def _segment_duration(self, seg: Any) -> float:
        if seg is None:
            return 0.0
        if self._is_number(seg):
            return float(seg)
        if isinstance(seg, (tuple, list)):
            if len(seg) >= 2 and self._is_number(seg[0]) and self._is_number(seg[1]):
                return float(seg[1]) - float(seg[0])
            s = 0.0
            for v in seg:
                if self._is_number(v):
                    s += float(v)
            return s
        if isinstance(seg, dict):
            if "duration" in seg and self._is_number(seg["duration"]):
                return float(seg["duration"])
            if "work" in seg and self._is_number(seg["work"]):
                return float(seg["work"])
            if "done" in seg and self._is_number(seg["done"]):
                return float(seg["done"])
            if "start" in seg and "end" in seg and self._is_number(seg["start"]) and self._is_number(seg["end"]):
                return float(seg["end"]) - float(seg["start"])
            return 0.0
        try:
            if hasattr(seg, "duration") and self._is_number(seg.duration):
                return float(seg.duration)
        except Exception:
            pass
        return 0.0

    def _update_done_cache(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            self._tdt_id = tdt
            self._tdt_mode = None
            self._tdt_sum = 0.0
            self._tdt_len = 0
            return 0.0

        if tdt is not self._tdt_id:
            self._tdt_id = tdt
            self._tdt_mode = None
            self._tdt_sum = 0.0
            self._tdt_len = 0

        ln = len(tdt)

        if self._tdt_mode is None:
            if ln >= 2 and all(self._is_number(x) for x in tdt):
                monotone = True
                prev = float(tdt[0])
                for i in range(1, ln):
                    cur = float(tdt[i])
                    if cur < prev:
                        monotone = False
                        break
                    prev = cur
                task_dur = float(getattr(self, "task_duration", 0.0) or 0.0)
                if monotone and (task_dur <= 0.0 or float(tdt[-1]) <= 1.05 * task_dur):
                    self._tdt_mode = "cumulative"
                else:
                    self._tdt_mode = "sum"
            else:
                self._tdt_mode = "sum"

        if self._tdt_mode == "cumulative":
            val = float(tdt[-1]) if ln else 0.0
            return max(0.0, val)

        if ln == self._tdt_len:
            return self._tdt_sum

        if ln > self._tdt_len:
            for i in range(self._tdt_len, ln):
                self._tdt_sum += self._segment_duration(tdt[i])
            self._tdt_len = ln
            return self._tdt_sum

        s = 0.0
        for seg in tdt:
            s += self._segment_duration(seg)
        self._tdt_sum = s
        self._tdt_len = ln
        return s

    def _get_remaining_work(self) -> float:
        done = self._update_done_cache()
        task_dur = float(getattr(self, "task_duration", 0.0) or 0.0)
        if task_dur <= 0.0:
            return 0.0
        rem = task_dur - done
        if rem < 0.0:
            rem = 0.0
        return rem

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_initialized()

        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)

        time_left = deadline - elapsed
        remaining_work = self._get_remaining_work()

        if remaining_work <= 0.0:
            self._commit_to_od = False
            self._cooldown_steps = 0
            return ClusterType.NONE

        if last_cluster_type != ClusterType.NONE and self._cooldown_steps > 0:
            self._cooldown_steps -= 1

        if self._commit_to_od:
            decision = ClusterType.ON_DEMAND
        else:
            if time_left <= remaining_work + self._commit_buffer:
                self._commit_to_od = True
                decision = ClusterType.ON_DEMAND
            else:
                slack = time_left - remaining_work

                if has_spot:
                    if last_cluster_type == ClusterType.ON_DEMAND and self._cooldown_steps > 0:
                        decision = ClusterType.ON_DEMAND
                    else:
                        decision = ClusterType.SPOT
                else:
                    if slack > self._idle_buffer:
                        if last_cluster_type == ClusterType.ON_DEMAND and self._cooldown_steps == 0 and slack > self._stop_buffer:
                            decision = ClusterType.NONE
                        else:
                            decision = ClusterType.NONE if last_cluster_type != ClusterType.ON_DEMAND else ClusterType.ON_DEMAND
                    else:
                        decision = ClusterType.ON_DEMAND

        if decision == ClusterType.SPOT and not has_spot:
            decision = ClusterType.ON_DEMAND

        if decision == ClusterType.NONE:
            self._cooldown_steps = 0
        else:
            if decision != last_cluster_type:
                self._cooldown_steps = self._cooldown_on_switch_steps

        return decision

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)