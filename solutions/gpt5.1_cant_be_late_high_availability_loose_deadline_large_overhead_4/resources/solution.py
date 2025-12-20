import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__(args)
        self._committed_on_demand = False
        self._safety_buffer_seconds = None
        self._initialized_runtime = False
        self._last_elapsed = None

    def solve(self, spec_path: str) -> "Solution":
        self.spec_path = spec_path
        # Runtime-related fields will be initialized on first _step call
        self._committed_on_demand = False
        self._safety_buffer_seconds = None
        self._initialized_runtime = False
        self._last_elapsed = None
        return self

    def _initialize_runtime(self):
        # Called on first _step when env is available
        # Choose a conservative safety buffer in seconds.
        # Based on provided values: deadline slack 22h, restart_overhead ~0.2h.
        # We keep at least ~4h margin plus multiple restart_overheads.
        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
        overhead = getattr(self, "restart_overhead", 0.0) or 0.0

        base_margin = 4.0 * 3600.0  # 4 hours in seconds
        overhead_based = 6.0 * overhead + 2.0 * gap
        self._safety_buffer_seconds = max(base_margin, overhead_based)

        self._committed_on_demand = False
        self._initialized_runtime = True
        self._last_elapsed = self.env.elapsed_seconds

    def _compute_work_remaining(self) -> float:
        # task_duration and task_done_time are in seconds
        done = 0.0
        if getattr(self, "task_done_time", None):
            # Sum of completed work segments
            done = float(sum(self.task_done_time))
        remaining = float(self.task_duration) - done
        if remaining < 0.0:
            remaining = 0.0
        return remaining

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._initialized_runtime:
            self._initialize_runtime()

        # Basic environment info
        t = float(self.env.elapsed_seconds)
        dt = float(self.env.gap_seconds)
        deadline = float(self.deadline)

        # Remaining required work (in seconds)
        remaining_work = self._compute_work_remaining()

        # If work is fully done, no need to run more
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Time until deadline
        time_to_deadline = deadline - t

        # If already at/after deadline, just run OD to minimize additional delay
        if time_to_deadline <= 0.0:
            return ClusterType.ON_DEMAND

        # Slack in wall-clock time if we were to run remaining_work immediately
        # on on-demand without further interruptions.
        # slack_total = (deadline - current_time) - remaining_work
        slack_total = time_to_deadline - remaining_work

        # Initialize safety buffer if needed
        if self._safety_buffer_seconds is None:
            gap = dt
            overhead = getattr(self, "restart_overhead", 0.0) or 0.0
            base_margin = 4.0 * 3600.0
            overhead_based = 6.0 * overhead + 2.0 * gap
            self._safety_buffer_seconds = max(base_margin, overhead_based)

        safety_buffer = self._safety_buffer_seconds
        overhead = getattr(self, "restart_overhead", 0.0) or 0.0

        # If, even now, pure on-demand from this moment cannot finish before
        # deadline with safety buffer, we still choose ON_DEMAND to try to catch up.
        # This situation should be rare; missing deadline is very penalized.
        if slack_total <= 0.0:
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        # Decide whether to permanently commit to on-demand only.
        if not self._committed_on_demand:
            # If remaining slack is at or below safety_buffer, commit to OD.
            if slack_total <= safety_buffer:
                self._committed_on_demand = True

        if self._committed_on_demand:
            # Once committed, always use on-demand until task completion.
            return ClusterType.ON_DEMAND

        # We have ample slack left (slack_total > safety_buffer).
        # Further restrict use of spot to times when we have enough extra slack
        # beyond safety buffer to tolerate a worst-case immediate restart_overhead.
        min_slack_for_spot = safety_buffer + overhead
        if slack_total <= min_slack_for_spot:
            # Too little slack to risk another spot interruption; switch to OD.
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        # We are still in the "flexible" region where spot is allowed.

        if has_spot:
            # Prefer cheap spot when available and safe.
            return ClusterType.SPOT

        # No spot available. Decide between waiting (NONE) and using expensive OD.
        # If waiting this step (duration dt) would push slack down to/below
        # safety_buffer, start on-demand instead.
        if slack_total - dt <= safety_buffer:
            # Not enough slack to afford waiting; use OD now.
            return ClusterType.ON_DEMAND

        # We can safely wait for spot without jeopardizing deadline.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
