import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cant-Be-Late multi-region scheduling strategy."""

    NAME = "cb_late_multi_v1"

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

        # Custom state
        self._initialized = False
        self._prev_task_done_len = 0
        self._work_done_seconds = 0.0
        self._force_on_demand = False
        self._safety_margin_seconds = 0.0

        # Scalarized parameters (set in _lazy_init)
        self._task_duration = None
        self._restart_overhead = None
        self._deadline = None
        self._gap_seconds = None

        return self

    def _lazy_init(self) -> None:
        if self._initialized:
            return

        # Extract scalar task duration (seconds)
        td = getattr(self, "task_duration", None)
        if isinstance(td, (list, tuple)):
            self._task_duration = float(td[0])
        else:
            self._task_duration = float(td)

        # Extract scalar restart overhead (seconds)
        ro = getattr(self, "restart_overhead", None)
        if isinstance(ro, (list, tuple)):
            self._restart_overhead = float(ro[0])
        else:
            self._restart_overhead = float(ro)

        # Extract scalar deadline (seconds)
        dl = getattr(self, "deadline", None)
        self._deadline = float(dl)

        # Time per decision step (seconds)
        gap = getattr(self.env, "gap_seconds", None)
        if gap is None:
            gap = 0.0
        self._gap_seconds = float(gap)

        # Initial slack = time_left - work_left - one_restart_overhead
        initial_slack = self._deadline - self._task_duration - self._restart_overhead

        if initial_slack <= 0:
            # Degenerate case: no slack; choose minimal safe margin
            margin = max(self._gap_seconds + self._restart_overhead, self._restart_overhead)
        else:
            # Base margin accounts for at most one "bad" step that can consume
            # up to gap + restart_overhead time without progress.
            base_margin = max(
                2.0 * (self._gap_seconds + self._restart_overhead),
                5.0 * self._restart_overhead,
            )
            raw_margin = min(initial_slack * 0.5, base_margin)
            # Ensure margin is at least one worst-case step drop in slack.
            min_required_margin = self._gap_seconds + self._restart_overhead
            margin = max(raw_margin, min_required_margin)

        self._safety_margin_seconds = margin
        self._initialized = True

    def _update_work_done(self) -> None:
        """Incrementally track total work done to avoid O(n^2) summation."""
        cur_len = len(self.task_done_time)
        if cur_len > self._prev_task_done_len:
            delta = 0.0
            for i in range(self._prev_task_done_len, cur_len):
                delta += self.task_done_time[i]
            self._work_done_seconds += delta
            self._prev_task_done_len = cur_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._initialized:
            self._lazy_init()

        # Update our cached progress
        self._update_work_done()

        remaining_work = self._task_duration - self._work_done_seconds
        if remaining_work <= 0:
            # Task already complete: do not run more
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_left = self._deadline - elapsed

        # If somehow beyond deadline, still choose ON_DEMAND to minimize further loss
        if time_left <= 0:
            return ClusterType.ON_DEMAND

        # Slack beyond what is needed to finish using only on-demand from now:
        # slack = time_left - (remaining_work + one_restart_overhead)
        slack = time_left - remaining_work - self._restart_overhead

        # Once slack is small, irrevocably switch to on-demand to guarantee completion
        if (not self._force_on_demand) and (slack <= self._safety_margin_seconds):
            self._force_on_demand = True

        if self._force_on_demand:
            # From this point on, always use on-demand
            return ClusterType.ON_DEMAND

        # Before forcing on-demand: use Spot whenever available, otherwise wait
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE