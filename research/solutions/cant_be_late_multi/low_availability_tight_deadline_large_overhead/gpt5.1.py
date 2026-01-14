import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Initialize cached scalar parameters (seconds)
        td = getattr(self, "task_duration", None)
        if isinstance(td, (list, tuple)):
            self._task_total_duration = float(td[0])
        else:
            self._task_total_duration = float(td)

        ro = getattr(self, "restart_overhead", None)
        if isinstance(ro, (list, tuple)):
            self._restart_overhead_scalar = float(ro[0])
        else:
            self._restart_overhead_scalar = float(ro)

        dl = getattr(self, "deadline", None)
        if isinstance(dl, (list, tuple)):
            self._deadline_scalar = float(dl[0])
        else:
            self._deadline_scalar = float(dl)

        # Progress tracking
        td_list = getattr(self, "task_done_time", [])
        self._last_td_len = len(td_list)
        self._total_done = float(sum(td_list)) if td_list else 0.0

        # Fallback state
        self._fallback_committed = False

        return self

    def _update_progress(self) -> None:
        td_list = self.task_done_time
        n = len(td_list)
        if n > self._last_td_len:
            # Sum only newly added segments to keep O(1) amortized per step
            self._total_done += float(sum(td_list[self._last_td_len:]))
            self._last_td_len = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Lazy initialization safety (in case _step called before solve, though unlikely)
        if not hasattr(self, "_total_done"):
            td_list = getattr(self, "task_done_time", [])
            self._last_td_len = len(td_list)
            self._total_done = float(sum(td_list)) if td_list else 0.0
            self._fallback_committed = False
            # Cache scalar params
            td = getattr(self, "task_duration", None)
            if isinstance(td, (list, tuple)):
                self._task_total_duration = float(td[0])
            else:
                self._task_total_duration = float(td)
            ro = getattr(self, "restart_overhead", None)
            if isinstance(ro, (list, tuple)):
                self._restart_overhead_scalar = float(ro[0])
            else:
                self._restart_overhead_scalar = float(ro)
            dl = getattr(self, "deadline", None)
            if isinstance(dl, (list, tuple)):
                self._deadline_scalar = float(dl[0])
            else:
                self._deadline_scalar = float(dl)

        # Update accumulated progress
        self._update_progress()

        remaining_work = self._task_total_duration - self._total_done
        if remaining_work <= 0.0:
            # Task completed; no need to run further.
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        remaining_time = self._deadline_scalar - elapsed

        # If we've already committed to on-demand, keep using it.
        if self._fallback_committed:
            return ClusterType.ON_DEMAND

        restart_overhead = self._restart_overhead_scalar

        # Time required if we start on-demand immediately (worst case).
        fallback_time_needed = remaining_work + restart_overhead

        # If even starting on-demand now can't finish by deadline, still choose on-demand.
        if remaining_time <= fallback_time_needed:
            self._fallback_committed = True
            return ClusterType.ON_DEMAND

        gap = self.env.gap_seconds
        step_dur = gap if remaining_time > gap else remaining_time

        # Worst case: we waste this entire step (no useful work).
        remaining_time_after_idle = remaining_time - step_dur

        # If no time left after this step or can't finish with on-demand then, commit now.
        if remaining_time_after_idle <= 0.0:
            self._fallback_committed = True
            return ClusterType.ON_DEMAND

        if remaining_time_after_idle < (remaining_work + restart_overhead):
            self._fallback_committed = True
            return ClusterType.ON_DEMAND

        # Safe to "gamble" this step: prefer Spot when available, otherwise wait.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE