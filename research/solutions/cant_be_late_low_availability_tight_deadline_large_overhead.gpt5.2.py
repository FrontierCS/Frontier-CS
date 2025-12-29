import json
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


def _clamp(x: float, lo: float, hi: float) -> float:
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self.args = args

        self._steps = 0
        self._ewma_p = 0.20
        self._ewma_alpha = 0.02

        self._spot_down_steps = 0
        self._spot_up_steps = 0
        self._last_has_spot: Optional[bool] = None

        self._od_forced = False
        self._od_since: Optional[float] = None

        self._spec = {}

    def solve(self, spec_path: str) -> "Solution":
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                txt = f.read().strip()
            if txt:
                try:
                    self._spec = json.loads(txt)
                except Exception:
                    try:
                        import yaml  # type: ignore

                        self._spec = yaml.safe_load(txt) or {}
                    except Exception:
                        self._spec = {}
        except Exception:
            self._spec = {}
        return self

    def _estimate_done_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0
        if isinstance(td, (int, float)):
            v = float(td)
            if v < 0:
                return 0.0
            return v
        if isinstance(td, list):
            if not td:
                return 0.0

            # list of numeric entries
            if all(isinstance(x, (int, float)) for x in td):
                vals = [float(x) for x in td]
                if not vals:
                    return 0.0
                last = vals[-1]
                sumv = sum(vals)
                nondecreasing = all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1))
                dur = float(getattr(self, "task_duration", 0.0) or 0.0)
                if nondecreasing and dur > 0 and last <= dur * 1.05 and sumv > max(last * 1.5, dur * 1.1):
                    return max(0.0, last)
                return max(0.0, sumv)

            total = 0.0
            for seg in td:
                if isinstance(seg, (tuple, list)) and len(seg) >= 2:
                    a, b = seg[0], seg[1]
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        total += float(b) - float(a)
                elif isinstance(seg, dict):
                    if "duration" in seg and isinstance(seg["duration"], (int, float)):
                        total += float(seg["duration"])
                    elif "start" in seg and "end" in seg and isinstance(seg["start"], (int, float)) and isinstance(seg["end"], (int, float)):
                        total += float(seg["end"]) - float(seg["start"])
            return max(0.0, total)

        return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._steps += 1
        obs = 1.0 if has_spot else 0.0
        self._ewma_p = (1.0 - self._ewma_alpha) * self._ewma_p + self._ewma_alpha * obs

        if self._last_has_spot is None or has_spot != self._last_has_spot:
            if has_spot:
                self._spot_up_steps = 1
                self._spot_down_steps = 0
            else:
                self._spot_down_steps = 1
                self._spot_up_steps = 0
        else:
            if has_spot:
                self._spot_up_steps += 1
                self._spot_down_steps = 0
            else:
                self._spot_down_steps += 1
                self._spot_up_steps = 0
        self._last_has_spot = has_spot

        done = self._estimate_done_seconds()
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        remaining_work = max(0.0, task_duration - done)

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        remaining_time = max(0.0, deadline - elapsed)

        if remaining_work <= 0.0:
            self._od_forced = False
            self._od_since = None
            return ClusterType.NONE

        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        endgame_buffer = max(1800.0, 2.0 * overhead, 2.0 * gap)
        panic_buffer = max(3600.0, 4.0 * overhead, 2.0 * gap)

        slack = remaining_time - remaining_work

        if remaining_time <= remaining_work + endgame_buffer or slack <= endgame_buffer:
            self._od_forced = True

        if self._od_forced:
            if self._od_since is None:
                self._od_since = elapsed
            return ClusterType.ON_DEMAND

        p = _clamp(self._ewma_p, 0.05, 0.95)
        extra_reserve = (max(0.0, 0.30 - p) / 0.30) * (2.0 * 3600.0)  # up to 2 hours extra reserve
        wait_threshold = panic_buffer + extra_reserve

        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                if self._od_since is None:
                    self._od_since = max(0.0, elapsed - gap)
                od_run = elapsed - self._od_since
                min_od_run = max(30.0 * 60.0, 2.0 * overhead)

                if od_run < min_od_run:
                    return ClusterType.ON_DEMAND

                # Only switch back to spot if it looks stable and we have room for another restart.
                if self._spot_up_steps >= 2 and remaining_work > max(3600.0, 3.0 * overhead) and slack > (wait_threshold + overhead):
                    self._od_since = None
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND

            self._od_since = None
            return ClusterType.SPOT

        # spot not available
        if last_cluster_type == ClusterType.ON_DEMAND:
            if self._od_since is None:
                self._od_since = max(0.0, elapsed - gap)
            return ClusterType.ON_DEMAND

        if p >= 0.25:
            down_limit = 8
        elif p >= 0.15:
            down_limit = 4
        else:
            down_limit = 1

        if slack > wait_threshold and self._spot_down_steps <= down_limit:
            self._od_since = None
            return ClusterType.NONE

        if self._od_since is None:
            self._od_since = elapsed
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)