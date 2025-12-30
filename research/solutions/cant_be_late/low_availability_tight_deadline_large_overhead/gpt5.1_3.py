import argparse
from typing import Any

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except ImportError:
    # Fallback definitions for local testing; in the real evaluation
    # environment, the above imports will succeed and these will be ignored.
    from enum import Enum

    class ClusterType(Enum):
        SPOT = 1
        ON_DEMAND = 2
        NONE = 3

    class Strategy:
        def __init__(self, *args, **kwargs):
            self.env = type("Env", (), {})()
            self.env.elapsed_seconds = 0.0
            self.env.gap_seconds = 0.0
            self.env.cluster_type = ClusterType.NONE
            self.task_duration = 0.0
            self.task_done_time = []
            self.deadline = 0.0
            self.restart_overhead = 0.0


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args: Any = None):
        # Try to call parent constructor in a flexible way.
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except TypeError:
                pass

        self.args = args
        # Per-run state (reset when env.elapsed_seconds goes backwards)
        self.progress_seconds = 0.0
        self.last_elapsed = 0.0
        self.lock_to_od = False
        self._params_initialized = False
        self.GUARD_TIME = 0.0
        self.IDLE_BUFFER = 0.0

    def solve(self, spec_path: str) -> "Solution":
        # Optional initialization; currently unused.
        return self

    def _reset_run_state(self):
        self.progress_seconds = 0.0
        self.last_elapsed = self.env.elapsed_seconds
        self.lock_to_od = False
        self._params_initialized = False
        self.GUARD_TIME = 0.0
        self.IDLE_BUFFER = 0.0

    def _init_run_params(self):
        # Initialize guard and idle buffer based on slack and restart overhead.
        deadline = getattr(self, "deadline", 0.0) or 0.0
        task_duration = getattr(self, "task_duration", 0.0) or 0.0
        restart = getattr(self, "restart_overhead", 0.0) or 0.0

        slack = max(deadline - task_duration, 0.0)

        if slack > 0.0:
            # Guard time: fraction of slack, at least half of restart, at most half slack.
            guard_candidate = max(slack * 0.2, restart * 0.5)
            self.GUARD_TIME = min(guard_candidate, slack * 0.5)

            # Idle buffer: smaller fraction of slack, at least one restart, at most 30% slack.
            idle_candidate = max(slack * 0.1, restart)
            self.IDLE_BUFFER = min(idle_candidate, slack * 0.3)
        else:
            # No slack: be conservative.
            self.GUARD_TIME = restart
            self.IDLE_BUFFER = restart

        # Ensure strictly positive if restart_overhead is positive.
        if restart > 0.0:
            if self.GUARD_TIME <= 0.0:
                self.GUARD_TIME = 0.5 * restart
            if self.IDLE_BUFFER <= 0.0:
                self.IDLE_BUFFER = restart

        self._params_initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Detect new episode by a decrease in elapsed time.
        current_elapsed = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
        if current_elapsed < self.last_elapsed - 1e-6:
            self._reset_run_state()

        # Initialize per-run parameters once we have env attributes.
        if not self._params_initialized:
            self._init_run_params()

        # Update our estimate of completed work based on actual running time.
        dt = current_elapsed - self.last_elapsed
        if dt > 0.0 and last_cluster_type in (ClusterType.SPOT, ClusterType.ON_DEMAND):
            self.progress_seconds += dt
        self.last_elapsed = current_elapsed

        # Compute remaining work and time.
        task_duration = getattr(self, "task_duration", 0.0) or 0.0
        deadline = getattr(self, "deadline", 0.0) or 0.0
        restart_overhead = getattr(self, "restart_overhead", 0.0) or 0.0

        remaining_work = max(task_duration - self.progress_seconds, 0.0)
        time_to_deadline = max(deadline - current_elapsed, 0.0)

        # If we are effectively done, no need to run more instances.
        if remaining_work <= 0.0:
            self.lock_to_od = False
            return ClusterType.NONE

        # Decide whether to lock into on-demand for the rest of the job.
        if not self.lock_to_od:
            overhead_reserve = restart_overhead
            safe_margin = time_to_deadline - (remaining_work + overhead_reserve + self.GUARD_TIME)
            if safe_margin <= 0.0:
                self.lock_to_od = True

        # If locked, always run on on-demand.
        if self.lock_to_od:
            return ClusterType.ON_DEMAND

        # Not locked: speculative phase.
        if has_spot:
            # Prefer spot when available during speculative phase.
            return ClusterType.SPOT

        # Spot not available: decide between waiting (NONE) and temporary on-demand.
        overhead_reserve = restart_overhead
        safe_margin = time_to_deadline - (remaining_work + overhead_reserve + self.GUARD_TIME)

        if safe_margin > self.IDLE_BUFFER:
            # We have enough slack to wait for cheaper spot instances.
            return ClusterType.NONE

        # Slack is getting tight but not yet in lock-to-OD region; use OD to maintain progress.
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser) -> "Solution":
        args, _ = parser.parse_known_args()
        return cls(args)