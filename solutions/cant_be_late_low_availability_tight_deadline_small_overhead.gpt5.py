from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self._locked_to_od = False
        self._progress_cache = {"len": 0, "sum": 0.0}

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _reset_run_state_if_needed(self):
        # Detect new run by elapsed time near zero
        try:
            if self.env.elapsed_seconds <= (self.env.gap_seconds if hasattr(self.env, "gap_seconds") else 1.0) * 0.1:
                self._locked_to_od = False
                self._progress_cache = {"len": 0, "sum": 0.0}
        except Exception:
            # If env not yet fully initialized, keep defaults
            pass

    def _done_progress(self) -> float:
        # Efficiently sum task_done_time incrementally
        lst = self.task_done_time if self.task_done_time is not None else []
        l = len(lst)
        if l != self._progress_cache["len"]:
            total = self._progress_cache["sum"]
            for i in range(self._progress_cache["len"], l):
                total += lst[i]
            self._progress_cache["sum"] = total
            self._progress_cache["len"] = l
        return self._progress_cache["sum"]

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._reset_run_state_if_needed()

        dt = getattr(self.env, "gap_seconds", 60.0)
        fudge = 0.25 * dt  # small safety buffer to avoid boundary misses

        done = self._done_progress()
        remaining = max(0.0, float(self.task_duration) - done)
        if remaining <= 0.0:
            return ClusterType.NONE

        time_left = float(self.deadline) - float(self.env.elapsed_seconds)

        # If already committed to on-demand, stay on it to avoid risk/overhead
        if self._locked_to_od:
            return ClusterType.ON_DEMAND

        # Fallback overhead if we need to start on-demand from non-OD state
        fallback_overhead = float(self.restart_overhead)

        # If we're too close to deadline to risk anything, lock to on-demand now
        if time_left <= remaining + fallback_overhead + fudge:
            self._locked_to_od = True
            return ClusterType.ON_DEMAND

        # If spot not available, decide whether we can afford to wait one step
        if not has_spot:
            # If we can wait exactly one step and still have time to switch to OD and finish, wait
            if (time_left - dt) >= (remaining + fallback_overhead + fudge):
                return ClusterType.NONE
            # Otherwise, switch to on-demand now
            self._locked_to_od = True
            return ClusterType.ON_DEMAND

        # Spot is available and we have enough slack: use spot
        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
