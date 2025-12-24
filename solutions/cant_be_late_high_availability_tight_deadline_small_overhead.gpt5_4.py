import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cb_lsafety_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self._commit_od = False
        self._progress_sum = 0.0
        self._progress_len = 0
        self._guard_factor = getattr(args, "guard_factor", 2.0) if args is not None else 2.0
        self._min_guard_seconds = getattr(args, "min_guard_seconds", 5.0) if args is not None else 5.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _update_progress_sum(self):
        try:
            l = self.task_done_time
            if l is None:
                return
            new_len = len(l)
            if new_len > self._progress_len:
                self._progress_sum += sum(l[self._progress_len : new_len])
                self._progress_len = new_len
        except Exception:
            # Fallback: if anything goes wrong, compute directly (should rarely happen)
            try:
                self._progress_sum = float(sum(self.task_done_time))
                self._progress_len = len(self.task_done_time)
            except Exception:
                # As a last resort, leave progress as is
                pass

    def _remaining_work(self) -> float:
        self._update_progress_sum()
        try:
            total = float(self.task_duration)
        except Exception:
            total = 0.0
        done = min(max(self._progress_sum, 0.0), total)
        return max(total - done, 0.0)

    def _safe_guard(self) -> float:
        try:
            gap = float(self.env.gap_seconds)
        except Exception:
            gap = 60.0
        guard = max(self._min_guard_seconds, self._guard_factor * gap)
        return guard

    def _must_commit_od(self, last_cluster_type: ClusterType) -> bool:
        # Compute if we need to start on-demand now to guarantee finishing before deadline
        try:
            now = float(self.env.elapsed_seconds)
        except Exception:
            now = 0.0
        try:
            deadline = float(self.deadline)
        except Exception:
            # If deadline is missing, be conservative: commit to OD
            return True

        remaining_work = self._remaining_work()
        if remaining_work <= 0.0:
            return False

        try:
            restart_overhead = float(self.restart_overhead)
        except Exception:
            restart_overhead = 0.0

        # Overhead to start OD now is zero if we are already on OD; else restart_overhead
        od_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead

        guard = self._safe_guard()
        rem_wall = deadline - now
        # If remaining wall time is less than or equal to work + overhead + guard,
        # we must commit to OD now.
        return rem_wall <= (remaining_work + od_overhead + guard)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If task already done, no need to run anything
        if self._remaining_work() <= 0.0:
            return ClusterType.NONE

        # If we've already committed to OD, continue using OD to avoid thrashing
        if self._commit_od:
            return ClusterType.ON_DEMAND

        # Check if we must commit to OD now to guarantee deadline
        if self._must_commit_od(last_cluster_type):
            self._commit_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, prefer Spot when available; else wait (NONE)
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        if isinstance(parser, argparse.ArgumentParser):
            parser.add_argument("--guard_factor", type=float, default=2.0)
            parser.add_argument("--min_guard_seconds", type=float, default=5.0)
        args, _ = parser.parse_known_args()
        return cls(args)
