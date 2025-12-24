import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._initialized = False
        self._prev_type: ClusterType = ClusterType.NONE
        self._overhead_remaining: float = 0.0
        self._ever_od: bool = False

        self._steps_total: int = 0
        self._steps_spot_avail: int = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _is_number(x: Any) -> bool:
        return isinstance(x, (int, float)) and not (isinstance(x, float) and (math.isnan(x) or math.isinf(x)))

    def _compute_done_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0
        if self._is_number(tdt):
            return float(tdt)

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        gap = float(getattr(getattr(self, "env", None), "gap_seconds", 0.0) or 0.0)

        if isinstance(tdt, (list, tuple)):
            if not tdt:
                return 0.0

            # Try structured segments first.
            seg_total = 0.0
            structured = False
            for seg in tdt:
                if seg is None:
                    continue
                if isinstance(seg, dict):
                    if "duration" in seg and self._is_number(seg["duration"]):
                        seg_total += float(seg["duration"])
                        structured = True
                    elif "start" in seg and "end" in seg and self._is_number(seg["start"]) and self._is_number(seg["end"]):
                        seg_total += float(seg["end"]) - float(seg["start"])
                        structured = True
                    elif "done" in seg and self._is_number(seg["done"]):
                        seg_total += float(seg["done"])
                        structured = True
                elif isinstance(seg, (list, tuple)) and len(seg) >= 2 and self._is_number(seg[0]) and self._is_number(seg[1]):
                    seg_total += float(seg[1]) - float(seg[0])
                    structured = True

            if structured:
                return max(0.0, min(seg_total, task_duration if task_duration > 0 else seg_total))

            # Numeric list ambiguity: could be per-segment durations (sum) or cumulative (use last/max).
            nums = []
            for v in tdt:
                if self._is_number(v):
                    nums.append(float(v))
                else:
                    try:
                        nums.append(float(v))
                    except Exception:
                        pass

            if not nums:
                return 0.0

            s = sum(nums)
            m = max(nums)
            last = nums[-1]

            # Heuristic:
            # - if sum is clearly too large, treat as cumulative.
            # - else treat as segment durations.
            if task_duration > 0.0 and s > task_duration + max(2.0 * gap, 1.0):
                done = max(last, m)
            else:
                done = s

            if task_duration > 0.0:
                done = max(0.0, min(done, task_duration))
            else:
                done = max(0.0, done)
            return done

        try:
            return float(tdt)
        except Exception:
            return 0.0

    def _safety_buffer_seconds(self) -> float:
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        H = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        # Robust against step granularity & bookkeeping mismatch.
        return max(2.0 * H, 10.0 * gap, 1800.0)

    def _update_internal_overhead(self, last_cluster_type: ClusterType) -> None:
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)

        # Resync if evaluator behavior differs.
        if not self._initialized:
            self._prev_type = last_cluster_type
            self._overhead_remaining = 0.0
            self._initialized = True
            if last_cluster_type == ClusterType.ON_DEMAND:
                self._ever_od = True
            return

        if last_cluster_type != self._prev_type:
            # Best-effort resync; if cluster got forced off, overhead should be irrelevant.
            if last_cluster_type == ClusterType.NONE:
                self._overhead_remaining = 0.0
            else:
                self._overhead_remaining = min(self._overhead_remaining, float(getattr(self, "restart_overhead", 0.0) or 0.0))

        if last_cluster_type in (ClusterType.SPOT, ClusterType.ON_DEMAND):
            self._overhead_remaining = max(0.0, self._overhead_remaining - gap)
        else:
            self._overhead_remaining = 0.0

        self._prev_type = last_cluster_type
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._ever_od = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_internal_overhead(last_cluster_type)

        self._steps_total += 1
        if has_spot:
            self._steps_spot_avail += 1

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        H = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        S = self._safety_buffer_seconds()

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        done = self._compute_done_seconds()
        if task_duration > 0.0:
            done = max(0.0, min(done, task_duration))
        remaining = max(0.0, task_duration - done) if task_duration > 0.0 else max(0.0, -done)

        if remaining <= 1e-6:
            self._prev_type = ClusterType.NONE
            self._overhead_remaining = 0.0
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0.0:
            # Deadline passed; best effort: keep running on-demand if possible.
            self._ever_od = True
            self._prev_type = ClusterType.ON_DEMAND
            self._overhead_remaining = H if last_cluster_type != ClusterType.ON_DEMAND else self._overhead_remaining
            return ClusterType.ON_DEMAND

        # If we've ever started on-demand, never switch back.
        if self._ever_od:
            choice = ClusterType.ON_DEMAND
        else:
            # Time-to-finish if we switch/start on-demand now.
            overhead_od_now = self._overhead_remaining if last_cluster_type == ClusterType.ON_DEMAND else H
            time_needed_od = overhead_od_now + remaining

            # If we wait one more step (NONE), we'd lose 'gap' time and still need full OD overhead later.
            can_wait_one = (time_left - gap) >= (remaining + H + S)

            must_start_od = (time_needed_od + S) >= time_left

            if not has_spot:
                if must_start_od or not can_wait_one:
                    choice = ClusterType.ON_DEMAND
                else:
                    choice = ClusterType.NONE
            else:
                # Spot available.
                if must_start_od:
                    choice = ClusterType.ON_DEMAND
                else:
                    # Avoid starting spot from non-spot when too close: worst-case pay spot restart + OD restart (2H) with no progress.
                    if last_cluster_type != ClusterType.SPOT and time_left < (remaining + 2.0 * H + S):
                        choice = ClusterType.ON_DEMAND
                    else:
                        choice = ClusterType.SPOT

        # Enforce constraint.
        if choice == ClusterType.SPOT and not has_spot:
            choice = ClusterType.ON_DEMAND if not self._ever_od else ClusterType.ON_DEMAND

        # Update internal overhead for next step based on this choice.
        if choice == ClusterType.NONE:
            self._overhead_remaining = 0.0
        else:
            if choice == last_cluster_type:
                # continue; overhead_remaining already reflects state at start of this step.
                pass
            else:
                self._overhead_remaining = H

        self._prev_type = choice
        if choice == ClusterType.ON_DEMAND:
            self._ever_od = True

        return choice

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
