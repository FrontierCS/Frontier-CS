import math
from typing import Any, Iterable

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_slack_wait"

    def __init__(self, args: Any = None):
        super().__init__(args)
        # Whether we've initialized thresholds based on environment/task
        self._initialized = False

        # Total slack time (seconds): deadline - task_duration
        self.slack_total = 0.0

        # Threshold of wasted time beyond which we commit to on-demand only
        self.commit_threshold = 0.0

        # Whether we've permanently switched to on-demand only
        self.commit_to_od = False

        # Waiting-for-spot state
        self.waiting_for_spot = False
        self.wait_start_time = None  # type: float | None

        # Max time to wait (idle) for spot per outage (seconds)
        self.max_wait_per_outage = 0.0

    def solve(self, spec_path: str) -> "Solution":
        # Optional: could read spec_path here; not needed for this strategy
        return self

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

    # ----------------- Helper Methods ----------------- #

    def _initialize_if_needed(self):
        if self._initialized:
            return

        # Use provided environment/task attributes
        # All times are assumed to be in seconds.
        task_duration = float(getattr(self, "task_duration", 0.0))
        deadline = float(getattr(self, "deadline", task_duration))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))

        # Total slack available
        self.slack_total = max(0.0, deadline - task_duration)

        # Commit threshold: once total wasted time reaches this, switch to OD-only.
        # We leave room for at most one more restart_overhead after committing.
        if self.slack_total <= 0.0:
            # No slack: never risk spot / idle; run OD from start.
            self.commit_threshold = 0.0
            self.commit_to_od = True
        else:
            # Conservative: ensure commit_threshold + restart_overhead <= slack_total
            self.commit_threshold = max(
                0.0,
                min(self.slack_total - 2.0 * restart_overhead, self.slack_total * 0.9),
            )
            if self.commit_threshold < 0.0:
                self.commit_threshold = 0.0

        # Max intentional idle time per outage.
        # Use at most half of commit_threshold, capped at 1 hour.
        self.max_wait_per_outage = min(3600.0, self.commit_threshold * 0.5)

        self._initialized = True

    def _compute_done_time(self) -> float:
        """Robustly compute total completed work time from self.task_done_time."""
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return 0.0

        total = 0.0
        for seg in segments:
            # Simple scalar duration
            if isinstance(seg, (int, float)):
                total += float(seg)
                continue

            # Iterable segment, try as (start, end)
            try:
                it = iter(seg)  # type: ignore
                vals = list(it)
                if len(vals) == 2:
                    start, end = vals
                    total += float(end) - float(start)
                elif len(vals) == 1:
                    total += float(vals[0])
                # Otherwise, ignore unrecognized formats
            except Exception:
                # Fallback: try casting whole object to float
                try:
                    total += float(seg)  # type: ignore
                except Exception:
                    continue
        return max(0.0, total)

    # ----------------- Core Decision Logic ----------------- #

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_if_needed()

        env = self.env
        elapsed = float(env.elapsed_seconds)

        # Compute total completed work and wasted time so far.
        done = self._compute_done_time()
        wasted = max(0.0, elapsed - done)

        # If we've already used too much slack, permanently switch to on-demand.
        if not self.commit_to_od and wasted >= self.commit_threshold:
            self.commit_to_od = True
            self.waiting_for_spot = False
            self.wait_start_time = None

        if self.commit_to_od:
            # From now on, always run on-demand to avoid further waste.
            return ClusterType.ON_DEMAND

        # Below: commit_to_od is False, so we still opportunistically use spot/idle.

        # If spot is available, always take it (cheaper, same speed).
        if has_spot:
            self.waiting_for_spot = False
            self.wait_start_time = None
            return ClusterType.SPOT

        # has_spot is False from here on.

        # Decide whether we are entering or continuing a "wait for spot" phase.
        if last_cluster_type == ClusterType.SPOT and not self.waiting_for_spot:
            # Just lost spot: start a waiting period.
            self.waiting_for_spot = True
            self.wait_start_time = elapsed

        if self.waiting_for_spot:
            # How long have we been waiting in this outage?
            wait_start = self.wait_start_time if self.wait_start_time is not None else elapsed
            time_waited = max(0.0, elapsed - wait_start)

            # Remaining slack budget before we must commit.
            time_budget_left = max(0.0, self.commit_threshold - wasted)

            # Decide whether we can afford to idle for one more step.
            # Only idle if:
            #  - We still have budget for at least one more gap,
            #  - We haven't exceeded per-outage wait limit.
            if (
                time_budget_left > env.gap_seconds
                and time_waited < self.max_wait_per_outage
            ):
                return ClusterType.NONE
            else:
                # Stop waiting and fall back to on-demand.
                self.waiting_for_spot = False
                self.wait_start_time = None
                return ClusterType.ON_DEMAND

        # Not waiting for spot (e.g., we were already on on-demand).
        # With no spot and not intentionally waiting, use on-demand to keep progress.
        return ClusterType.ON_DEMAND