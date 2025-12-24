from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "jit_fallback_robust_v1"

    def solve(self, spec_path: str) -> "Solution":
        # Initialize per-episode state
        self._commit_on_demand = False
        self._episode_id_marker = None
        return self

    def _reset_episode_if_needed(self):
        # Reset commit flag at the start of each episode/run
        # Using elapsed_seconds to detect new episode (assumed to reset to 0)
        if not hasattr(self, "_episode_id_marker"):
            self._episode_id_marker = 0
        # When a new env/run starts, elapsed_seconds should be 0 at the first step
        if getattr(self.env, "elapsed_seconds", None) is not None and self.env.elapsed_seconds == 0:
            self._commit_on_demand = False
            self._episode_id_marker += 1

    def _compute_remaining(self):
        completed = sum(self.task_done_time) if getattr(self, "task_done_time", None) else 0.0
        remaining = max(0.0, self.task_duration - completed)
        return remaining

    def _should_commit_now(self, time_remaining_s, remaining_s, gap_s, overhead_s):
        # Safety margin to account for discrete steps and any small uncertainties.
        # Use a conservative margin: at least twice the step, or the overhead (whichever is larger).
        margin_s = max(2.0 * gap_s, overhead_s)
        critical_s = remaining_s + overhead_s + margin_s
        return time_remaining_s <= critical_s

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._reset_episode_if_needed()

        # If task already complete, do nothing
        remaining_s = self._compute_remaining()
        if remaining_s <= 0:
            return ClusterType.NONE

        # Gather environment parameters
        gap_s = getattr(self.env, "gap_seconds", 60.0)
        time_now_s = getattr(self.env, "elapsed_seconds", 0.0)
        deadline_s = getattr(self, "deadline", time_now_s + remaining_s)
        time_remaining_s = max(0.0, deadline_s - time_now_s)
        overhead_s = float(getattr(self, "restart_overhead", 0.0))

        # If already committed to on-demand, keep using it
        if getattr(self, "_commit_on_demand", False):
            return ClusterType.ON_DEMAND

        # If we must commit now to guarantee finishing on OD (with buffer), do it
        if self._should_commit_now(time_remaining_s, remaining_s, gap_s, overhead_s):
            self._commit_on_demand = True
            return ClusterType.ON_DEMAND

        # Opportunistic use of spot if available and not at commit threshold
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: decide whether to wait or switch to OD now.
        # If waiting one more step would force an immediate commit next step, commit now.
        would_force_commit_next = self._should_commit_now(
            max(0.0, time_remaining_s - gap_s), remaining_s, gap_s, overhead_s
        )
        if would_force_commit_next:
            self._commit_on_demand = True
            return ClusterType.ON_DEMAND

        # Otherwise, wait for spot to return (pause to save cost)
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
