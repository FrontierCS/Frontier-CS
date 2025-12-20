from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cbl_heuristic_wait_spot"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _ensure_internal_state(self):
        if not hasattr(self, "_internal_initialized"):
            self._only_on_demand = False
            self._task_progress = 0.0
            self._last_task_done_len = 0
            self._internal_initialized = True

    def _update_task_progress(self):
        # Incrementally update total completed work from task_done_time segments.
        segments = getattr(self, "task_done_time", None)
        if segments is None:
            return
        curr_len = len(segments)
        if curr_len > self._last_task_done_len:
            # Sum only newly added segments.
            self._task_progress += sum(
                segments[self._last_task_done_len : curr_len]
            )
            self._last_task_done_len = curr_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_internal_state()
        self._update_task_progress()

        # Remaining work (in seconds).
        remaining = max(self.task_duration - self._task_progress, 0.0)

        # If task is done, no need to run more.
        if remaining <= 0:
            return ClusterType.NONE

        # Once we commit to on-demand, never go back to spot to avoid deadline risk.
        if self._only_on_demand:
            return ClusterType.ON_DEMAND

        # Time parameters.
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        overhead = getattr(self, "restart_overhead", 0.0)

        # Conservative safety margin: assume we may still need one restart_overhead
        # before progress resumes, and we make no progress during the next gap.
        # We can safely "wait" (NONE or SPOT) this step only if:
        #   elapsed + gap + overhead + remaining <= deadline
        safe_wait_until = self.deadline - remaining - overhead - gap

        if elapsed >= safe_wait_until:
            # Not enough slack left to risk waiting or relying on spot;
            # switch to on-demand for the rest of the job.
            self._only_on_demand = True
            return ClusterType.ON_DEMAND

        # We still have sufficient slack: use spot when available, otherwise wait.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
