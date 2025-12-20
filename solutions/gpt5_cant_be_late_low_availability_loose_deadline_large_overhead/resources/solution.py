from typing import Any, List, Union
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_threshold_v3"

    def __init__(self, args: Any = None):
        super().__init__(args)
        # Base buffer in seconds; can be overridden by args if provided
        buf_minutes = getattr(args, "buffer_minutes", 5.0) if args is not None else 5.0
        try:
            self.base_buffer_seconds = float(buf_minutes) * 60.0
        except Exception:
            self.base_buffer_seconds = 300.0
        self._committed_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _sum_done_seconds(self) -> float:
        done = 0.0
        segments: List[Union[float, int, list, tuple, dict]] = getattr(self, "task_done_time", []) or []
        for seg in segments:
            try:
                if isinstance(seg, (tuple, list)) and len(seg) >= 2:
                    s0, s1 = float(seg[0]), float(seg[1])
                    done += max(0.0, s1 - s0)
                elif isinstance(seg, dict) and "duration" in seg:
                    done += float(seg["duration"])
                else:
                    done += float(seg)
            except Exception:
                continue
        # Clamp to task_duration if it exists
        try:
            td = float(self.task_duration)
            if td >= 0:
                done = min(done, td)
        except Exception:
            pass
        return max(0.0, done)

    def _remaining_work_seconds(self) -> float:
        try:
            td = float(self.task_duration)
        except Exception:
            td = 0.0
        done = self._sum_done_seconds()
        return max(0.0, td - done)

    def _time_left_seconds(self) -> float:
        try:
            deadline = float(self.deadline)
            now = float(self.env.elapsed_seconds)
            return max(0.0, deadline - now)
        except Exception:
            return 0.0

    def _dynamic_buffer_seconds(self) -> float:
        # Combine static buffer with fractions of restart_overhead and gap to guard discretization
        try:
            gap = float(self.env.gap_seconds)
        except Exception:
            gap = 60.0
        try:
            rto = float(self.restart_overhead)
        except Exception:
            rto = 0.0
        # Buffer is at least half a gap and at least a fraction of overhead
        dyn = max(self.base_buffer_seconds, 0.25 * rto, 0.5 * gap)
        # Cap minimal to 60 seconds to ensure non-zero
        return max(dyn, 60.0)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If task is already done, do nothing
        remaining = self._remaining_work_seconds()
        if remaining <= 0.0:
            return ClusterType.NONE

        time_left = self._time_left_seconds()
        gap = float(getattr(self.env, "gap_seconds", 60.0))
        rto = float(getattr(self, "restart_overhead", 0.0))
        buffer_sec = self._dynamic_buffer_seconds()

        # If we're already committed to on-demand, stick with it to avoid restart overheads and guarantee finish
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # If we're in or past the critical region where OD is required to finish in time, commit to OD
        # Overhead needed if we start OD now:
        # - If we are currently on OD, overhead is 0 (no restart to stay on OD)
        # - Else, we need to pay restart_overhead once when starting OD
        overhead_needed_now = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else rto

        # Check whether we must commit right now to guarantee finish
        # We use: time_left <= remaining + overhead + buffer
        if time_left <= remaining + overhead_needed_now + buffer_sec:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, we can afford not to pay for OD now.
        # Prefer SPOT when available since it is cheaper and progresses the job.
        if has_spot:
            return ClusterType.SPOT

        # No spot available:
        # If we still have slack even after accounting for paying overhead later when switching to OD,
        # we can pause (NONE). Evaluate conservatively with overhead = rto.
        if time_left > remaining + rto + buffer_sec:
            return ClusterType.NONE

        # We're running low on slack and spot is unavailable: switch to OD to keep schedule.
        self._committed_to_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        try:
            parser.add_argument("--buffer_minutes", type=float, default=5.0, help="Safety buffer minutes before deadline to commit to on-demand.")
        except Exception:
            # In case parser is not standard; ignore
            pass
        args, _ = parser.parse_known_args()
        return cls(args)
