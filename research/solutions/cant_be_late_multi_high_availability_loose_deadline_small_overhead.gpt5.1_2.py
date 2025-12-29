import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with slack-aware Spot/On-Demand choice."""

    NAME = "slack_safe_spot_strategy"

    def solve(self, spec_path: str) -> "Solution":
        """Initialize the solution from spec_path config."""
        with open(spec_path) as f:
            config = json.load(f)

        duration_hours = float(config["duration"])
        deadline_hours = float(config["deadline"])
        overhead_hours = float(config["overhead"])

        args = Namespace(
            deadline_hours=deadline_hours,
            task_duration_hours=[duration_hours],
            restart_overhead_hours=[overhead_hours],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Store our own copies in seconds to avoid relying on internal names.
        self._task_duration_seconds = duration_hours * 3600.0
        self._deadline_seconds = deadline_hours * 3600.0
        self._restart_overhead_seconds = overhead_hours * 3600.0

        # This will be initialized on first _step call when env is ready.
        self._initialized_step = False

        return self

    def _initialize_step_state(self):
        """Lazy initialization when env is available."""
        self._initialized_step = True

        # Gap between environment steps (seconds).
        gap = float(getattr(self.env, "gap_seconds", 3600.0))
        self._gap_seconds = gap

        # Safety margin of slack time (seconds).
        # Heuristic: at least 10% of task duration, and at least ~2*gap + 2*overhead.
        task_dur = self._task_duration_seconds
        restart_o = self._restart_overhead_seconds
        self.safety_margin = max(
            0.1 * task_dur,
            2.0 * gap + 2.0 * restart_o,
            4.0 * restart_o,
        )

        # Track cumulative work done without O(n^2) summations.
        segs = self.task_done_time
        self._last_done_len = len(segs)
        total_done = 0.0
        for x in segs:
            total_done += x
        self._total_done = total_done

        # Once we flip to ON_DEMAND, we stick to it until completion.
        self.force_on_demand = False

    def _update_progress(self):
        """Incrementally update total work done from task_done_time list."""
        segs = self.task_done_time
        n = len(segs)
        if n > self._last_done_len:
            total_done = self._total_done
            for i in range(self._last_done_len, n):
                total_done += segs[i]
            self._total_done = total_done
            self._last_done_len = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        if not self._initialized_step:
            self._initialize_step_state()

        # Update cumulative progress.
        self._update_progress()

        # If already finished, do nothing.
        if self._total_done >= self._task_duration_seconds - 1e-6:
            return ClusterType.NONE

        remaining_work = self._task_duration_seconds - self._total_done
        remaining_time = self._deadline_seconds - self.env.elapsed_seconds

        # Compute time slack: how much extra time we have beyond minimal on-demand run.
        slack = remaining_time - remaining_work

        # If slack is small, or we are dangerously close to deadline, switch to on-demand.
        if not self.force_on_demand:
            if (
                slack <= self.safety_margin
                or remaining_time <= remaining_work + self._restart_overhead_seconds
            ):
                self.force_on_demand = True

        if self.force_on_demand:
            # Always run on on-demand to guarantee completion.
            return ClusterType.ON_DEMAND

        # In the "relaxed" phase: prefer Spot when available, otherwise idle to save cost.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable and we are still in relaxed phase; idle to save money.
        return ClusterType.NONE