import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with deadline guarantees and cost awareness."""

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

        # Normalize task duration and restart overhead to scalars in seconds.
        td = getattr(self, "task_duration", None)
        if isinstance(td, (list, tuple)):
            self.total_work = float(td[0])
        else:
            self.total_work = float(td)

        dl = getattr(self, "deadline", None)
        self.deadline_seconds = float(dl)

        ro = getattr(self, "restart_overhead", None)
        if isinstance(ro, (list, tuple)):
            self.restart_overhead_seconds = float(ro[0])
        else:
            self.restart_overhead_seconds = float(ro)

        self.total_slack = max(self.deadline_seconds - self.total_work, 0.0)

        # Heuristic thresholds:
        # - panic_slack: when remaining effective slack falls below this, we hard-commit to on-demand.
        #   Ensure it's at least 2 * restart_overhead to safely absorb a switch.
        # - conservative_slack: above this we are comfortable idling when spot is unavailable.
        if self.total_slack > 0.0:
            panic_base_frac = 0.2 * self.total_slack
            panic_base_over = 2.0 * self.restart_overhead_seconds
            panic_slack = max(panic_base_frac, panic_base_over)
            self.panic_slack = min(self.total_slack, panic_slack)

            cons_base_frac = 0.6 * self.total_slack
            cons_base_over = 5.0 * self.restart_overhead_seconds
            cons_slack = max(cons_base_frac, cons_base_over)
            self.conservative_slack = min(self.total_slack, cons_slack)

            if self.conservative_slack < self.panic_slack:
                self.conservative_slack = self.panic_slack
        else:
            self.panic_slack = 0.0
            self.conservative_slack = 0.0

        # Running sum of completed work (seconds)
        self._done_sum = 0.0
        self._last_task_segments_len = 0

        # Once we hard-commit to on-demand near the deadline, we never go back to spot.
        self._hard_commit_to_on_demand = False

        return self

    def _update_done_sum(self) -> float:
        """Incrementally maintain sum(self.task_done_time) in O(1) amortized time."""
        segments = self.task_done_time
        n = len(segments)
        if n > self._last_task_segments_len:
            s = 0.0
            for i in range(self._last_task_segments_len, n):
                s += segments[i]
            self._done_sum += s
            self._last_task_segments_len = n
        return self._done_sum

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update completed work.
        done = self._update_done_sum()

        # If work is already complete, run nothing.
        remaining_work = self.total_work - done
        if remaining_work <= 0.0:
            return ClusterType.NONE

        t = self.env.elapsed_seconds
        time_left = self.deadline_seconds - t
        if time_left <= 0.0:
            # Already at/past deadline; nothing we do now helps.
            return ClusterType.NONE

        # Pending restart overhead that will consume time before progress resumes.
        pending_overhead = getattr(self, "remaining_restart_overhead", 0.0) or 0.0

        # Effective slack: time left minus minimal required work and pending overhead.
        # This is the remaining "waste budget" (idle time + future overhead) before missing the deadline.
        slack = time_left - remaining_work - pending_overhead

        # If effective slack already negative, it's mathematically impossible to meet the deadline
        # even with perfect on-demand from now; still, we try to maximize progress.
        if slack < 0.0:
            self._hard_commit_to_on_demand = True
            return ClusterType.ON_DEMAND

        # If we haven't hard-committed yet and slack falls below panic threshold, do so now.
        if (not self._hard_commit_to_on_demand) and (slack <= self.panic_slack):
            self._hard_commit_to_on_demand = True

        # Once hard-committed, always use on-demand to avoid any further risk.
        if self._hard_commit_to_on_demand:
            return ClusterType.ON_DEMAND

        gap = self.env.gap_seconds

        # Safe zone: substantial slack remaining and not in hard-commit mode.
        if has_spot:
            # Prefer spot whenever it's available and we are not in emergency mode.
            return ClusterType.SPOT
        else:
            # Spot unavailable; decide between idling and on-demand.
            # Only idle if, after idling one more gap, we remain comfortably above conservative threshold.
            threshold_idle = max(self.conservative_slack, self.panic_slack, 0.0)
            slack_after_idle = slack - gap

            if slack_after_idle > threshold_idle:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND