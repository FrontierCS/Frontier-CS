from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__(args)
        self._commit_od = False
        self._last_elapsed = -1.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _reset_run_state_if_needed(self):
        # Detect a new run by a reset in elapsed time
        current_elapsed = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
        if self._last_elapsed < 0 or current_elapsed < self._last_elapsed:
            self._commit_od = False
        self._last_elapsed = current_elapsed

    def _remaining_work(self) -> float:
        done = 0.0
        if getattr(self, "task_done_time", None):
            try:
                done = float(sum(self.task_done_time))
            except Exception:
                # Fallback in case of unexpected structure
                done = 0.0
        total = float(getattr(self, "task_duration", 0.0) or 0.0)
        rem = total - done
        return rem if rem > 0 else 0.0

    def _time_left(self) -> float:
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        tl = deadline - elapsed
        return tl if tl > 0 else 0.0

    def _should_commit_to_od(self) -> bool:
        # Robust bail-out rule:
        # Continue on spot/wait only if even in the worst case of losing one step (gap)
        # plus paying one restart overhead, we can still finish on OD.
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        time_left = self._time_left()
        remaining = self._remaining_work()
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        # Required buffer to safely risk one more step:
        buffer_needed = overhead + gap
        # RBC = time_left - remaining
        rbc = time_left - remaining
        return rbc < buffer_needed

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._reset_run_state_if_needed()

        # If task is already completed, stop spending
        if self._remaining_work() <= 0.0:
            return ClusterType.NONE

        # Commit to OD if safety condition is breached
        if not self._commit_od and self._should_commit_to_od():
            self._commit_od = True

        if self._commit_od:
            return ClusterType.ON_DEMAND

        # Prefer spot when available and safe; otherwise wait; commit-to-OD handled above
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
