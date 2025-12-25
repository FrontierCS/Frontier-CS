from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_guarded_v1"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _reset_caches_if_needed(self):
        t = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
        if not hasattr(self, "_last_elapsed") or t < getattr(self, "_last_elapsed", -1.0):
            # New episode/run
            self._progress_cache = sum(self.task_done_time) if self.task_done_time else 0.0
            self._progress_len = len(self.task_done_time) if self.task_done_time else 0
        else:
            # Incremental update of progress cache
            if hasattr(self, "_progress_len"):
                n = len(self.task_done_time) if self.task_done_time else 0
                if n > self._progress_len:
                    self._progress_cache += sum(self.task_done_time[self._progress_len:n])
                    self._progress_len = n
            else:
                self._progress_cache = sum(self.task_done_time) if self.task_done_time else 0.0
                self._progress_len = len(self.task_done_time) if self.task_done_time else 0
        self._last_elapsed = t

    def _remaining_work(self) -> float:
        # Returns remaining work in seconds
        total = float(self.task_duration)
        done = float(self._progress_cache)
        rem = total - done
        return rem if rem > 0.0 else 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Maintain caches
        self._reset_caches_if_needed()

        # Basic parameters
        t = float(self.env.elapsed_seconds)
        gap = float(self.env.gap_seconds)
        deadline = float(self.deadline)
        overhead = float(self.restart_overhead)

        # Remaining work
        R = self._remaining_work()
        if R <= 0.0:
            return ClusterType.NONE

        # If already on On-Demand, keep it to avoid unnecessary risk/cost from switching
        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        slack = deadline - t

        # Helper checks
        def can_finish_if_start_od_now():
            # If we start OD now, we must pay restart overhead then process R
            return (overhead + R) <= slack

        def can_wait_one_step():
            # If we wait for one step, at t+gap we must still be able to start OD and finish
            return (overhead + R) <= (slack - gap)

        def can_start_spot_now():
            # If starting SPOT now (from non-SPOT), worst case: immediate preemption after paying overhead,
            # then we start OD and pay another overhead. Require 2*overhead + R <= slack.
            return (2.0 * overhead + R) <= slack

        def can_continue_spot_now():
            # If continuing on SPOT (no new start overhead this step),
            # we require that even if preempted immediately, starting OD now works: overhead + R <= slack.
            return (overhead + R) <= slack

        # Decision logic
        if has_spot:
            if last_cluster_type == ClusterType.SPOT:
                # Continue on SPOT if safe; else bail out to OD
                if can_continue_spot_now():
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                # Starting SPOT from NONE or other state
                if can_start_spot_now():
                    return ClusterType.SPOT
                else:
                    # Not safe to start SPOT; use OD if it can still finish
                    if can_finish_if_start_od_now():
                        return ClusterType.ON_DEMAND
                    else:
                        # If even OD can't finish, still choose OD to minimize lateness
                        return ClusterType.ON_DEMAND
        else:
            # No SPOT availability: either wait (NONE) if safe, else switch to OD
            if can_wait_one_step():
                return ClusterType.NONE
            else:
                # Must switch to OD to make deadline
                if can_finish_if_start_od_now():
                    return ClusterType.ON_DEMAND
                else:
                    return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)