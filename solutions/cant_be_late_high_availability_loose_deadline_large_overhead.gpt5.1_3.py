from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _initialize_if_needed(self):
        if getattr(self, "_policy_inited", False):
            return

        # Initial slack: extra time beyond minimal compute time
        try:
            initial_slack = max(self.deadline - self.task_duration, 0.0)
        except Exception:
            initial_slack = 0.0

        self.initial_slack = initial_slack

        gap = getattr(self.env, "gap_seconds", 60.0)
        restart_overhead = getattr(self, "restart_overhead", 0.0)

        # Commit threshold: when slack <= commit_slack, force pure on-demand
        if initial_slack > 0:
            commit_by_fraction = 0.05 * initial_slack  # keep ~5% of slack as reserve
        else:
            commit_by_fraction = restart_overhead + 2 * gap

        base_commit = restart_overhead + 2 * gap  # ensure >= overhead + safety
        self.commit_slack = max(base_commit, commit_by_fraction)

        # Do not let commit_slack exceed initial_slack too much
        if initial_slack > 0 and self.commit_slack > initial_slack:
            # At least keep some buffer, but within reasonable bound
            self.commit_slack = max(initial_slack * 0.5, base_commit)

        # Tolerance for deviation from planned slack consumption
        self.budget_tolerance = max(2 * gap, 0.01 * initial_slack)

        self.force_od_phase = False
        self._policy_inited = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_if_needed()

        # Compute total work done so far
        work_done = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining_work = max(self.task_duration - work_done, 0.0)

        # If task already done, do nothing
        if remaining_work <= 0:
            return ClusterType.NONE

        now = self.env.elapsed_seconds
        deadline = self.deadline
        gap = self.env.gap_seconds

        remaining_time = max(deadline - now, 0.0)
        slack = remaining_time - remaining_work

        # If slack already very negative, we are in trouble: use OD aggressively
        if slack < -gap:
            return ClusterType.ON_DEMAND

        # Enter final safety phase when slack becomes low
        if not self.force_od_phase and slack <= self.commit_slack:
            self.force_od_phase = True

        if self.force_od_phase:
            # Final phase: always on-demand to avoid further risk
            return ClusterType.ON_DEMAND

        # Progress-based slack budgeting
        initial_slack = self.initial_slack
        if initial_slack > 0 and self.task_duration > 0:
            progress = work_done / self.task_duration
            spent_slack_actual = initial_slack - slack
            spent_slack_target = initial_slack * progress
            behind = spent_slack_actual > spent_slack_target + self.budget_tolerance
        else:
            # If configuration is degenerate, act conservatively
            behind = True

        if behind:
            # Behind budget: avoid consuming more slack.
            # Run compute whenever possible: SPOT if available, else OD.
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        else:
            # On or ahead of budget: use spot; let slack absorb outages.
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
