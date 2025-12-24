import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_slack_v1"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self._initialized = False
        self._force_on_demand = False
        self._safety_margin_s = 0.0
        self._min_deadline_buffer_s = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _lazy_init(self) -> None:
        if self._initialized:
            return
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)

        # Safety margin to cover: (i) restart overhead on final switch to OD,
        # (ii) step granularity, and (iii) small additional buffer.
        # Keep it modest to avoid excessive early OD usage.
        buf = min(600.0, 0.002 * task_duration)  # up to 10 minutes; ~0.1h for 48h job
        self._safety_margin_s = max(2.2 * overhead + 2.0 * gap, overhead + 4.0 * gap) + buf

        # Always keep at least one step of buffer before deadline when forcing OD.
        self._min_deadline_buffer_s = max(gap, 0.5 * overhead)

        self._initialized = True

    def _done_work_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            for a in ("task_done_seconds", "done_seconds", "progress_seconds"):
                v = getattr(self.env, a, None)
                if isinstance(v, (int, float)):
                    return float(v)
            return 0.0

        if isinstance(tdt, (int, float)):
            return float(tdt)

        if isinstance(tdt, (list, tuple)):
            if len(tdt) == 0:
                return 0.0

            first = tdt[0]
            if isinstance(first, (int, float)):
                # Heuristic: if it looks like a non-decreasing list of cumulative totals, use last.
                nondecreasing = True
                for i in range(1, len(tdt)):
                    try:
                        if float(tdt[i]) < float(tdt[i - 1]):
                            nondecreasing = False
                            break
                    except Exception:
                        nondecreasing = False
                        break
                if nondecreasing:
                    try:
                        last = float(tdt[-1])
                        if last >= 0.0:
                            return last
                    except Exception:
                        pass
                try:
                    return float(sum(float(x) for x in tdt))
                except Exception:
                    return 0.0

            if isinstance(first, (list, tuple)) and len(first) >= 2:
                total = 0.0
                for seg in tdt:
                    if not (isinstance(seg, (list, tuple)) and len(seg) >= 2):
                        continue
                    a, b = seg[0], seg[1]
                    if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
                        continue
                    if b >= a:
                        total += float(b - a)
                    else:
                        # If it's (duration, something) or malformed, fall back to b as duration.
                        total += float(b)
                return total

        return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)

        done = self._done_work_seconds()
        if done < 0.0:
            done = 0.0
        if task_duration > 0.0 and done > task_duration:
            done = task_duration

        remaining_work = max(0.0, task_duration - done)
        remaining_time = max(0.0, deadline - elapsed)

        if remaining_work <= 0.0:
            return ClusterType.NONE

        # If we're extremely close to deadline, don't risk anything.
        if remaining_time <= self._min_deadline_buffer_s:
            return ClusterType.ON_DEMAND

        slack = remaining_time - remaining_work

        # Sticky on-demand mode near the end to avoid deadline misses due to spot interruptions / restarts.
        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        # Force OD when slack is low enough that another restart/step delay could cause a miss.
        if slack <= (self._safety_margin_s + gap):
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        # Otherwise: use spot whenever available; if spot is unavailable, pause to consume slack.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
