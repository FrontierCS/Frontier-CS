import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with guaranteed-deadline fallback."""

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

        # Normalize core parameters to scalars (seconds).
        task_duration_attr = getattr(self, "task_duration", None)
        if isinstance(task_duration_attr, (list, tuple)):
            self._task_duration = float(task_duration_attr[0])
        else:
            self._task_duration = float(task_duration_attr)

        restart_overhead_attr = getattr(self, "restart_overhead", None)
        if isinstance(restart_overhead_attr, (list, tuple)):
            self._restart_overhead = float(restart_overhead_attr[0])
        else:
            self._restart_overhead = float(restart_overhead_attr)

        deadline_attr = getattr(self, "deadline", None)
        if isinstance(deadline_attr, (list, tuple)):
            self._deadline = float(deadline_attr[0])
        else:
            self._deadline = float(deadline_attr)

        self._initialize_internal_state()
        return self

    def _initialize_internal_state(self) -> None:
        """Initialize or reset per-run internal state."""
        env = getattr(self, "env", None)
        gap = getattr(env, "gap_seconds", 0.0) if env is not None else 0.0
        overhead = getattr(self, "_restart_overhead", 0.0)

        # Guard time large enough to cover one full step plus a restart.
        self._guard_time = gap + overhead

        # Whether we've irrevocably switched to on-demand.
        self.force_on_demand = False

        # Cached total work done (seconds), to avoid O(n) sum each step.
        lst = getattr(self, "task_done_time", [])
        self._progress_list_len = len(lst)
        total = 0.0
        for v in lst:
            total += v
        self._total_work_done = total

        # Track elapsed time to detect environment resets.
        self._last_elapsed = getattr(env, "elapsed_seconds", 0.0) if env is not None else 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Detect environment reset by decreased elapsed time.
        current_elapsed = self.env.elapsed_seconds
        last_elapsed = getattr(self, "_last_elapsed", None)
        if last_elapsed is None or current_elapsed < last_elapsed:
            self._initialize_internal_state()
            current_elapsed = self.env.elapsed_seconds
        else:
            self._last_elapsed = current_elapsed

        # Ensure guard time is set (in case env was unavailable during solve()).
        if getattr(self, "_guard_time", None) is None:
            gap = getattr(self.env, "gap_seconds", 0.0)
            overhead = getattr(self, "_restart_overhead", 0.0)
            self._guard_time = gap + overhead

        # Incrementally update cached work done.
        lst = self.task_done_time
        n = len(lst)
        if n > self._progress_list_len:
            inc = 0.0
            for i in range(self._progress_list_len, n):
                inc += lst[i]
            self._total_work_done += inc
            self._progress_list_len = n

        work_left = self._task_duration - self._total_work_done
        if work_left <= 0.0:
            # Task complete.
            return ClusterType.NONE

        time_left = self._deadline - current_elapsed
        if time_left <= 0.0:
            # Already past deadline; nothing useful to do.
            return ClusterType.NONE

        # Decide whether to switch permanently to on-demand.
        if not self.force_on_demand:
            # Conservative: assume we will pay a full restart overhead
            # when we switch to on-demand.
            safe_slack = time_left - (work_left + self._restart_overhead)

            # Commit when slack is within one full step plus overhead.
            if safe_slack <= self._guard_time:
                self.force_on_demand = True

        if self.force_on_demand:
            return ClusterType.ON_DEMAND

        # Spot-preferred phase: use Spot whenever available; otherwise wait.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE