from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "safety_margin_deadline_guard_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self._locked_od = False
        self._prev_elapsed = -1.0
        self._done_sum = 0.0
        self._tdt_count = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _reset_if_new_trace(self):
        try:
            cur_elapsed = float(self.env.elapsed_seconds)
        except Exception:
            cur_elapsed = -1.0
        if cur_elapsed < self._prev_elapsed or cur_elapsed <= 0.0:
            self._locked_od = False
            self._done_sum = 0.0
            self._tdt_count = 0
        self._prev_elapsed = cur_elapsed

    def _update_done_sum(self):
        # Efficiently update total done work by processing only new segments.
        tdt = self.task_done_time
        if not isinstance(tdt, list):
            return
        if len(tdt) < self._tdt_count:
            # Environment reset; handled elsewhere, but guard anyway.
            self._done_sum = 0.0
            self._tdt_count = 0
        for seg in tdt[self._tdt_count:]:
            try:
                if isinstance(seg, dict):
                    if "duration" in seg:
                        self._done_sum += float(seg["duration"])
                    elif "start" in seg and "end" in seg:
                        self._done_sum += float(seg["end"]) - float(seg["start"])
                elif isinstance(seg, (list, tuple)) and len(seg) >= 2:
                    self._done_sum += float(seg[1]) - float(seg[0])
                else:
                    # Assume it's a numeric duration
                    v = float(seg)
                    if v > 0:
                        self._done_sum += v
            except Exception:
                # Ignore malformed entries
                pass
        self._tdt_count = len(tdt)

    def _remaining_work(self):
        self._update_done_sum()
        rem = max(self.task_duration - self._done_sum, 0.0)
        return rem

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._reset_if_new_trace()

        # If already locked to on-demand, keep using it to guarantee completion.
        if self._locked_od:
            return ClusterType.ON_DEMAND

        rem = self._remaining_work()
        time_left = max(self.deadline - self.env.elapsed_seconds, 0.0)

        # If no remaining work, do nothing.
        if rem <= 0.0:
            return ClusterType.NONE

        # Safety margin to handle discretization and overhead nuances.
        margin = max(float(getattr(self.env, "gap_seconds", 0.0)), 0.0)

        # Overhead incurred if switching to on-demand now (if we're not already on it).
        od_overhead_now = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else float(self.restart_overhead)

        # If we're currently on on-demand (but not locked), keep running it.
        # This avoids unnecessary switches and repeated overhead if evaluator starts us on OD.
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._locked_od = True
            return ClusterType.ON_DEMAND

        # Decision when spot is unavailable: choose OD if needed to meet deadline; else wait (NONE).
        if not has_spot:
            # If we cannot afford to wait (no progress this step), start OD now.
            if time_left <= rem + od_overhead_now + margin:
                self._locked_od = True
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE

        # Spot is available:
        # Prefer SPOT when available; it's safe to continue even near boundary since
        # time_left - (rem + restart_overhead) remains unchanged after a full spot step.
        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)