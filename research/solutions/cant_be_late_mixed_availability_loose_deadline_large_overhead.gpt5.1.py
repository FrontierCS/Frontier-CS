from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "time_safe_spot_first"

    def __init__(self, args):
        super().__init__(args)
        self.args = args
        self._committed_to_on_demand = False
        self._episode_start_time = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _reset_episode_state_if_needed(self):
        env = getattr(self, "env", None)
        if env is None:
            return
        # Detect new episode by elapsed_seconds reset to 0
        if self._episode_start_time is None or env.elapsed_seconds == 0:
            self._committed_to_on_demand = False
            self._episode_start_time = env.elapsed_seconds

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._reset_episode_state_if_needed()
        env = self.env
        t = env.elapsed_seconds
        gap = env.gap_seconds

        # Once we switch to on-demand, stay on it to avoid extra overhead or risk.
        if self._committed_to_on_demand:
            return ClusterType.ON_DEMAND

        # Check if it is still safe to wait one more full step without committing to on-demand.
        # Worst-case: zero progress so far and zero progress during this step.
        # After this step, we'll need restart_overhead + full task_duration time on on-demand.
        if not (t + gap + self.restart_overhead + self.task_duration <= self.deadline):
            # Need to start on-demand now to guarantee finishing before deadline.
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Still safe to wait: prefer spot when available, otherwise pause to save cost.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)