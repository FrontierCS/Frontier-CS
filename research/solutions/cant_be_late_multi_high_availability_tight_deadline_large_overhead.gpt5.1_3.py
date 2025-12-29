import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cant-Be-Late Multi-Region Scheduling Strategy."""

    NAME = "cant_be_late_safe_spot_priority_v1"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.

        The spec file contains:
        - deadline: deadline in hours
        - duration: task duration in hours
        - overhead: restart overhead in hours
        - trace_files: list of trace file paths (one per region)
        """
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Custom runtime state will be initialized on first _step call.
        self._initialized_runtime_state = False

        return self

    # ---- Internal helpers ----

    def _init_runtime(self) -> None:
        """Initialize per-run cached state (called on first _step)."""
        self._initialized_runtime_state = True

        # Cached total work done (in seconds).
        self._work_done = 0.0
        self._prev_task_len = len(getattr(self, "task_done_time", []))
        if self._prev_task_len > 0:
            # Sum once at start; afterwards we only incrementally add.
            self._work_done = float(sum(self.task_done_time))

        # Once we decide to use ON_DEMAND, we stick with it.
        self._committed_ondemand = False

        # Safety margin before deadline, in seconds.
        # Use at least 15 minutes or 10 steps, whichever is larger.
        gap = getattr(self.env, "gap_seconds", 1.0)
        self._safety_margin = max(15.0 * 60.0, 10.0 * gap)

        # Step counter (not used in logic but may be useful).
        self._step_count = 0

        # Number of regions (if available). We do not actively switch regions
        # in this strategy, but capturing this keeps us compatible.
        try:
            self._num_regions = self.env.get_num_regions()
        except Exception:
            self._num_regions = 1

    def _update_work_done_cache(self) -> None:
        """Incrementally update cached total work done from task_done_time."""
        td = self.task_done_time
        cur_len = len(td)
        if cur_len > self._prev_task_len:
            new_sum = 0.0
            for i in range(self._prev_task_len, cur_len):
                new_sum += td[i]
            self._work_done += new_sum
            self._prev_task_len = cur_len

    # ---- Core decision logic ----

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Lazy initialization once environment is ready.
        if not getattr(self, "_initialized_runtime_state", False):
            self._init_runtime()

        self._step_count += 1

        # Update cached total work done.
        self._update_work_done_cache()

        # If somehow already done, do nothing.
        if self._work_done >= self.task_duration:
            return ClusterType.NONE

        # If we're already running ON_DEMAND, stay with it.
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._committed_ondemand = True

        t = self.env.elapsed_seconds
        g = self.env.gap_seconds
        O = self.restart_overhead
        R = max(0.0, self.task_duration - self._work_done)
        D = self.deadline
        M = self._safety_margin

        if self._committed_ondemand:
            # Deterministic phase: always use On-Demand to avoid any risk.
            return ClusterType.ON_DEMAND

        # Determine if it's safe to spend this step without committing
        # to On-Demand (worst case: we gain no progress this step, then
        # next step we start ON_DEMAND and pay one restart overhead).
        #
        # Safety condition for *delaying* the switch:
        #   t + g (this step) + O (overhead when switching next step)
        #   + R (remaining work) + M (extra safety margin) <= D
        safe_to_delay = (t + g + O + R + M) <= D

        if not safe_to_delay:
            # We must start / stay on On-Demand now to guarantee finish.
            self._committed_ondemand = True
            return ClusterType.ON_DEMAND

        # In the safe region: minimize cost.
        # Prefer Spot if available, otherwise pause and wait.
        if has_spot:
            return ClusterType.SPOT

        # No Spot currently available: wait (no cost) and try again later.
        return ClusterType.NONE