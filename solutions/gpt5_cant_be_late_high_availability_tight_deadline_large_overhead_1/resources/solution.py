from typing import Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_guardrail_heuristic_v2"

    def solve(self, spec_path: str) -> "Solution":
        # Initialize persistent state
        self._initialized = False
        return self

    def _ensure_init(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.od_committed: bool = False
        self.wait_start_time: Optional[float] = None
        self.od_run_started_at: Optional[float] = None

    def _task_done(self) -> float:
        # Robustly compute completed work seconds
        try:
            return float(sum(self.task_done_time))
        except Exception:
            try:
                return float(self.task_done_time)  # type: ignore
            except Exception:
                return 0.0

    def _min_od_run_time(self, gap: float) -> float:
        # Minimum time to stay on OD before considering switching back to Spot
        # Aim to amortize two restart overheads (switch to SPOT and later back to OD)
        # Use at least 30 minutes and a few gaps.
        base = 30 * 60.0
        return max(3.0 * gap, base)

    def _commit_guard_margin(self, gap: float) -> float:
        # Safety buffer to avoid tight boundary due to discretization and unknowns
        return max(2.0 * gap, 180.0)  # at least 3 minutes

    def _slack_guard(self, gap: float) -> float:
        # Keep some slack reserve for future uncertainty
        return 0.35 * float(self.restart_overhead) + max(gap, 60.0)

    def _should_commit_to_od(self, last_cluster_type: ClusterType, time_left: float, remain: float, gap: float) -> bool:
        # Decide if we must commit to OD now to guarantee finish
        commit_need = remain + (0.0 if last_cluster_type == ClusterType.ON_DEMAND else float(self.restart_overhead))
        return time_left <= commit_need + self._commit_guard_margin(gap)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()

        now = float(self.env.elapsed_seconds)
        gap = float(self.env.gap_seconds)
        deadline = float(self.deadline)
        restart = float(self.restart_overhead)
        task_duration = float(self.task_duration)

        done = self._task_done()
        remain = max(0.0, task_duration - done)
        if remain <= 0.0:
            # Task finished
            return ClusterType.NONE

        time_left = max(0.0, deadline - now)
        slack_rem = time_left - remain  # may be negative if behind

        # Enforce commitment if needed
        if not self.od_committed and self._should_commit_to_od(last_cluster_type, time_left, remain, gap):
            self.od_committed = True
            self.wait_start_time = None
            # When committed, always run OD
            if last_cluster_type != ClusterType.ON_DEMAND:
                self.od_run_started_at = now
            return ClusterType.ON_DEMAND

        # If already committed, always choose ON_DEMAND
        if self.od_committed:
            self.wait_start_time = None
            if last_cluster_type != ClusterType.ON_DEMAND:
                self.od_run_started_at = now
            return ClusterType.ON_DEMAND

        # Not committed yet: opportunistically use spot, but guard deadline

        # If on OD already, track start time
        if last_cluster_type == ClusterType.ON_DEMAND and self.od_run_started_at is None:
            self.od_run_started_at = now

        # Helper headroom to allow waiting and/or switching costs
        headroom = time_left - (remain + restart)  # extra time above "switch to OD now" plan
        commit_guard = self._commit_guard_margin(gap)
        slack_guard = self._slack_guard(gap)

        # Case: Spot available
        if has_spot:
            # If we're not currently on OD, use SPOT
            if last_cluster_type != ClusterType.ON_DEMAND:
                self.wait_start_time = None
                self.od_run_started_at = None
                return ClusterType.SPOT

            # We are currently on OD: decide whether to switch back to SPOT
            # Require a minimum OD run duration to avoid thrashing
            od_run_dur = now - (self.od_run_started_at or now)
            if od_run_dur < self._min_od_run_time(gap):
                # Continue OD until minimum runtime reached
                return ClusterType.ON_DEMAND

            # Only switch back to spot if we have ample slack to absorb two restarts
            # and not too close to commit boundary
            if (slack_rem > 2.0 * restart + (0.5 * restart + max(gap, 60.0))) and (headroom > commit_guard + restart):
                # Switch back to spot
                self.wait_start_time = None
                self.od_run_started_at = None
                return ClusterType.SPOT
            else:
                # Keep OD to be safe
                return ClusterType.ON_DEMAND

        # Case: Spot unavailable
        if last_cluster_type == ClusterType.ON_DEMAND:
            # Already on OD; keep running
            self.wait_start_time = None
            return ClusterType.ON_DEMAND

        # Not on OD, and spot is unavailable -> decide to wait or switch to OD
        # Compute dynamic wait limit
        max_wait_by_commit = max(0.0, headroom - commit_guard)
        if slack_rem <= slack_guard or max_wait_by_commit <= 0.0:
            # Insufficient slack or headroom -> must use OD now
            self.wait_start_time = None
            self.od_run_started_at = now
            return ClusterType.ON_DEMAND

        # Final wait cap to avoid waiting too long in a single outage
        hard_wait_cap = 45.0 * 60.0  # 45 minutes
        final_wait_limit = min(max_wait_by_commit, max(0.0, slack_rem - slack_guard), hard_wait_cap)

        # Start or continue waiting
        if self.wait_start_time is None or last_cluster_type != ClusterType.NONE:
            self.wait_start_time = now

        waited = now - (self.wait_start_time or now)
        if waited < final_wait_limit:
            return ClusterType.NONE

        # Wait exceeded -> start OD
        self.wait_start_time = None
        self.od_run_started_at = now
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
