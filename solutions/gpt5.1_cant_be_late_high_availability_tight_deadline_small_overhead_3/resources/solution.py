from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_scheduler_v1"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _init_policy(self):
        self._policy_initialized = True
        env = getattr(self, "env", None)
        gap = getattr(env, "gap_seconds", 60.0) if env is not None else 60.0
        restart = float(getattr(self, "restart_overhead", 0.0))
        duration = float(getattr(self, "task_duration", 0.0))
        deadline = float(getattr(self, "deadline", duration))

        total_slack = max(0.0, deadline - duration)
        self.total_slack = total_slack

        if total_slack <= 0.0:
            # No slack: always run on-demand
            self.commit_slack = 0.0
            self.high_slack = 0.0
            self.revert_to_spot_slack = 0.0
        else:
            # Commit to on-demand when remaining slack is small
            self.commit_slack = max(4.0 * restart, 20.0 * gap, 0.1 * total_slack)
            if self.commit_slack > 0.5 * total_slack:
                self.commit_slack = 0.5 * total_slack

            # Above this, we can afford to sometimes idle waiting for spot
            self.high_slack = max(2.0 * self.commit_slack, 0.7 * total_slack)
            if self.high_slack > 0.9 * total_slack:
                self.high_slack = 0.9 * total_slack

            if self.commit_slack > self.high_slack:
                self.commit_slack = 0.5 * self.high_slack

            # When slack is reasonably big we can switch back to spot
            self.revert_to_spot_slack = max(self.commit_slack * 2.0, 0.2 * total_slack)
            if self.revert_to_spot_slack >= self.high_slack:
                self.revert_to_spot_slack = 0.7 * self.high_slack

        # Mode:
        # 0 = SPOT_ONLY (wait for spot, can idle)
        # 1 = SPOT_PREFERRED (spot when available, otherwise on-demand)
        # 2 = ON_DEMAND_ONLY (force on-demand)
        self.mode = 0

    def _get_work_done(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0
        if isinstance(tdt, (int, float)):
            return float(tdt)
        try:
            return float(sum(tdt))
        except TypeError:
            return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not getattr(self, "_policy_initialized", False):
            self._init_policy()

        env = self.env
        task_duration = float(getattr(self, "task_duration", 0.0))
        deadline = float(getattr(self, "deadline", float("inf")))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))
        gap = float(getattr(env, "gap_seconds", 60.0))

        work_done = self._get_work_done()
        remaining = max(0.0, task_duration - work_done)
        time_left = deadline - float(getattr(env, "elapsed_seconds", 0.0))

        if remaining <= 0.0 or time_left <= 0.0:
            return ClusterType.NONE

        slack = time_left - remaining

        # Hard safety guard: if even with a final restart we are near the deadline, force OD.
        if time_left <= remaining + restart_overhead + gap:
            self.mode = 2
        else:
            # Update mode based on slack; mode is monotone increasing.
            if slack <= self.commit_slack and self.mode < 2:
                self.mode = 2
            elif slack <= self.high_slack and self.mode < 1:
                self.mode = 1

        # Choose cluster based on mode and spot availability.
        if self.mode == 2:
            # ON_DEMAND_ONLY
            return ClusterType.ON_DEMAND

        if self.mode == 0:
            # SPOT_ONLY: use spot when available, otherwise idle.
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.NONE

        # mode == 1: SPOT_PREFERRED
        if has_spot:
            # Avoid switching back to spot when slack is very low and we were on OD.
            if last_cluster_type == ClusterType.ON_DEMAND and slack <= self.revert_to_spot_slack:
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
