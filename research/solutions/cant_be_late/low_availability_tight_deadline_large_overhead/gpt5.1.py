from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_spot_v1"

    def solve(self, spec_path: str) -> "Solution":
        # No spec-based configuration for now.
        return self

    def _initialize_slack_params(self):
        """Lazy initialization of slack-related parameters."""
        if hasattr(self, "_slack_params_initialized") and self._slack_params_initialized:
            return

        # Total slack allowed for non-work time (idle + overhead)
        total_slack = self.deadline - self.task_duration
        self._total_slack = total_slack

        # Default values
        self._allow_spot = False
        self._non_work_limit = 0.0
        self._idle_limit = 0.0

        # If no slack or unknown overhead, fall back to always on-demand.
        if total_slack <= 0:
            self._allow_spot = False
        else:
            # Margin after accounting for a possible final restart overhead.
            # We keep some extra safety margin (<1.0) to be robust.
            restart_overhead = max(self.restart_overhead, 0.0)
            margin = total_slack - restart_overhead
            if margin < 0.0:
                margin = 0.0

            # Tuning factors:
            # - threshold_factor: how much of (slack - restart_overhead) we use
            #   before permanently switching to on-demand.
            # - idle_factor: how much of that margin we are willing to spend on
            #   intentional idling while waiting for spot.
            threshold_factor = 0.9
            idle_factor = 0.5

            self._non_work_limit = threshold_factor * margin
            if self._non_work_limit < 0.0:
                self._non_work_limit = 0.0

            self._idle_limit = idle_factor * margin
            if self._idle_limit < 0.0:
                self._idle_limit = 0.0
            if self._idle_limit > self._non_work_limit:
                self._idle_limit = self._non_work_limit

            # Allow spot if we have any meaningful slack budget.
            self._allow_spot = self._non_work_limit > 0.0

        # Once this flag becomes True, we never go back to using spot.
        self._force_on_demand = not self._allow_spot
        self._slack_params_initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Ensure parameters are initialized once env is available.
        self._initialize_slack_params()

        # Compute total work done so far.
        work_segments = getattr(self, "task_done_time", None)
        if work_segments:
            work_done = float(sum(work_segments))
        else:
            work_done = 0.0

        # If task is already finished, do nothing (no cost).
        if work_done >= self.task_duration:
            return ClusterType.NONE

        current_time = float(self.env.elapsed_seconds)

        # Total non-work time so far (overhead + intentional idling).
        non_work_so_far = current_time - work_done
        if non_work_so_far < 0.0:
            non_work_so_far = 0.0

        # If we previously decided to never use spot again, stick to on-demand.
        if self._force_on_demand or not self._allow_spot:
            # Always choose on-demand while work remains.
            return ClusterType.ON_DEMAND

        # Check if we've exhausted the budget for non-work time.
        if non_work_so_far >= self._non_work_limit:
            # Permanently switch to on-demand from now on.
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        # We are still within non-work budget and allowed to use spot.

        # If spot is available, always use it (it's significantly cheaper).
        if has_spot:
            return ClusterType.SPOT

        # Spot is unavailable: decide between idling and on-demand.
        # If we haven't spent much of the non-work budget, we can afford to wait.
        if non_work_so_far < self._idle_limit:
            return ClusterType.NONE

        # Non-work budget for idling is mostly consumed; use on-demand to keep progress.
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)