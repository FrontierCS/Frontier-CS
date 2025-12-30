import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with deadline safety."""

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

        # Internal state (initialized later when env is available)
        self._initialized = False
        self._total_done = 0.0
        self._last_task_done_len = 0
        self._lock_to_ond = False
        self._preferred_region = None
        self._commit_threshold = 0.0
        self._initial_slack = 0.0
        self._task_duration_s = None
        self._restart_overhead_s = None
        self._deadline_s = None

        return self

    def _initialize_if_needed(self):
        if self._initialized:
            return
        self._initialized = True

        # Normalize possible list-valued attributes into scalars
        td = getattr(self, "task_duration", 0.0)
        if isinstance(td, (list, tuple)):
            td = float(td[0])
        self._task_duration_s = float(td)

        ro = getattr(self, "restart_overhead", 0.0)
        if isinstance(ro, (list, tuple)):
            ro = float(ro[0])
        self._restart_overhead_s = float(ro)

        dl = getattr(self, "deadline", 0.0)
        if isinstance(dl, (list, tuple)):
            dl = float(dl[0])
        self._deadline_s = float(dl)

        self._preferred_region = self.env.get_current_region()

        remaining_time = self._deadline_s - self.env.elapsed_seconds
        time_needed = self._task_duration_s + self._restart_overhead_s
        initial_slack = max(remaining_time - time_needed, 0.0)
        self._initial_slack = initial_slack

        gap = getattr(self.env, "gap_seconds", 0.0)
        base_thresh = 2.0 * (gap + self._restart_overhead_s)

        if initial_slack > 0.0:
            max_thresh = initial_slack * 0.8
            self._commit_threshold = min(base_thresh, max_thresh)
        else:
            self._commit_threshold = 0.0

    def _update_progress(self):
        td_list = self.task_done_time
        n = len(td_list)
        if n > self._last_task_done_len:
            self._total_done += sum(td_list[self._last_task_done_len:n])
            self._last_task_done_len = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_if_needed()
        self._update_progress()

        remaining_work = self._task_duration_s - self._total_done
        if remaining_work <= 0.0:
            # Task already completed.
            return ClusterType.NONE

        # Once locked into on-demand, never leave it until completion.
        if self._lock_to_ond:
            return ClusterType.ON_DEMAND

        remaining_time = self._deadline_s - self.env.elapsed_seconds
        if remaining_time <= 0.0:
            # Past deadline; nothing to do but run on-demand.
            self._lock_to_ond = True
            return ClusterType.ON_DEMAND

        # Conservative estimate of time needed if we switch to on-demand now.
        time_needed_ond = remaining_work + self._restart_overhead_s
        slack = remaining_time - time_needed_ond

        # If slack is small, commit to on-demand for safety.
        if slack <= self._commit_threshold:
            self._lock_to_ond = True
            return ClusterType.ON_DEMAND

        # Slack is large: we are in the "spot-preferred" phase.
        # Stay in our initial preferred region.
        if self._preferred_region is not None:
            current_region = self.env.get_current_region()
            if current_region != self._preferred_region:
                # Region switching is modeled as free in the provided API.
                self.env.switch_region(self._preferred_region)

        # Use Spot when available; otherwise, wait to save cost.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE