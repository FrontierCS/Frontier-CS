from typing import Any
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_solution"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args
        self._progress_sec = 0.0
        self._td_idx = 0
        self._od_committed = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _update_progress(self) -> float:
        # Safely accumulate progress from task_done_time list
        td = getattr(self, "task_done_time", None)
        if isinstance(td, list):
            n = len(td)
            if n > self._td_idx:
                added = 0.0
                for i in range(self._td_idx, n):
                    try:
                        v = float(td[i])
                    except Exception:
                        v = 0.0
                    added += v
                self._td_idx = n
                self._progress_sec += added
        # Clamp to task duration
        try:
            dur = float(self.task_duration)
        except Exception:
            dur = self._progress_sec
        if self._progress_sec > dur:
            self._progress_sec = dur
        return self._progress_sec

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update progress and remaining time
        done = self._update_progress()
        try:
            total = float(self.task_duration)
        except Exception:
            total = done
        remaining = max(0.0, total - done)

        # If already done, do nothing
        if remaining <= 0.0:
            self._od_committed = False
            return ClusterType.NONE

        # Time remaining until deadline
        try:
            elapsed = float(self.env.elapsed_seconds)
        except Exception:
            elapsed = 0.0
        try:
            deadline = float(self.deadline)
        except Exception:
            deadline = elapsed
        t_rem = max(0.0, deadline - elapsed)

        # If we are past the deadline, use OD (best effort)
        if t_rem <= 0.0:
            self._od_committed = True
            return ClusterType.ON_DEMAND

        # Parameters
        try:
            gap = float(self.env.gap_seconds)
        except Exception:
            gap = 60.0  # fallback 1 minute
        try:
            ovhd = float(self.restart_overhead)
        except Exception:
            ovhd = 180.0  # fallback 3 minutes

        # Safety buffer to handle discretization and overhead uncertainties
        safety = max(3.0 * gap, 2.0 * ovhd, 120.0)

        # If already committed to OD, keep running OD to avoid thrashing
        if self._od_committed:
            return ClusterType.ON_DEMAND

        # Determine if we must commit to OD now to guarantee deadline
        overhead_if_start_now = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else ovhd
        must_commit_now = t_rem <= (remaining + overhead_if_start_now + safety)

        if must_commit_now:
            self._od_committed = True
            return ClusterType.ON_DEMAND

        # Not forced yet: prefer Spot if available
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: decide to wait or start OD now
        # If we can't afford to wait one full gap, start OD now
        overhead_if_start_next = ovhd  # since we won't be on OD in the meantime
        cannot_wait_one_step = (t_rem - gap) <= (remaining + overhead_if_start_next + safety)
        if cannot_wait_one_step:
            self._od_committed = True
            return ClusterType.ON_DEMAND

        # Still enough slack to wait for Spot to return
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)