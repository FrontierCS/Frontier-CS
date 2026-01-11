import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy."""

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

        # Internal state initialization placeholders; actual init delayed to first _step
        self._internal_initialized = False
        return self

    # -------- Internal helpers --------

    def _initialize_internal(self):
        """Lazy initialization that depends on self.env being available."""
        self._internal_initialized = True

        # Gap size (seconds)
        self._dt = float(self.env.gap_seconds)

        # Restart overhead (seconds)
        ro = self.restart_overhead
        if isinstance(ro, (list, tuple)):
            ro = ro[0]
        self._restart_overhead = float(ro)

        # Task duration (seconds)
        td = self.task_duration
        if isinstance(td, (list, tuple)):
            td = td[0]
        self._task_duration_scalar = float(td)

        # Deadline (seconds)
        dl = self.deadline
        if isinstance(dl, (list, tuple)):
            dl = dl[0]
        self._deadline_scalar = float(dl)

        # Safe slack threshold (seconds) before we permanently switch to on-demand.
        # Set to (gap + overhead) so that even in the worst single-step slack loss,
        # we can still finish on-demand by the deadline after switching.
        self._commit_slack = self._dt + self._restart_overhead

        # When spot is unavailable, we are willing to wait (NONE) only if slack
        # is comfortably above the commit threshold by at least one time step.
        self._wait_slack_threshold = self._commit_slack + self._dt

        # Once this flag is set, we always choose ON_DEMAND thereafter.
        self._force_on_demand = False

        # Efficient running total of work done: avoid summing the list each step.
        self._last_task_len = 0
        self._total_work_done = 0.0

    def _update_work_done(self) -> float:
        """Update and return the total amount of work done so far (seconds)."""
        segments = self.task_done_time
        n = len(segments)
        if n > self._last_task_len:
            # Sum only new segments since last step.
            self._total_work_done += sum(segments[self._last_task_len : n])
            self._last_task_len = n
        return self._total_work_done

    # -------- Core decision logic --------

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not getattr(self, "_internal_initialized", False):
            self._initialize_internal()

        # Update progress and remaining work.
        work_done = self._update_work_done()
        remaining_work = self._task_duration_scalar - work_done

        # If somehow called after completion, avoid extra cost.
        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_remaining = self._deadline_scalar - elapsed

        # If already past deadline and not finished, further spending cannot avoid penalty.
        if time_remaining <= 0.0:
            return ClusterType.NONE

        # Slack = time remaining minus ideal time needed (no future overhead).
        slack_remaining = time_remaining - remaining_work

        # Decide whether to permanently switch to on-demand.
        if not self._force_on_demand:
            # When slack shrinks below the commit threshold, switch to on-demand
            # and never go back. Threshold chosen so we can still finish by
            # deadline even under worst-case future overhead patterns.
            if slack_remaining <= self._commit_slack:
                self._force_on_demand = True

        if self._force_on_demand:
            # Once forced, always run on-demand to guarantee completion.
            return ClusterType.ON_DEMAND

        # Pre-commit behavior:

        # Prefer Spot when available, to minimize cost.
        if has_spot:
            return ClusterType.SPOT

        # Spot not available:
        # If we have plenty of slack above the commit threshold, we can afford
        # to wait (NONE) for spot to return.
        if slack_remaining > self._wait_slack_threshold:
            return ClusterType.NONE

        # Slack getting tight but not yet at commit threshold: use on-demand
        # to keep making progress.
        return ClusterType.ON_DEMAND