from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_spot_first"

    def __init__(self, args):
        super().__init__(args)
        self.args = args
        self._committed_to_od = False
        self._initialized_env_params = False
        self._task_duration = None
        self._deadline = None
        self._restart_overhead = None
        self._gap_seconds = None

    def solve(self, spec_path: str) -> "Solution":
        # Reset per-spec state
        self._committed_to_od = False
        self._initialized_env_params = False
        self.spec_path = spec_path
        return self

    def _initialize_env_params(self):
        if self._initialized_env_params:
            return
        # These attributes are provided by the evaluation environment.
        self._task_duration = float(self.task_duration)
        self._deadline = float(self.deadline)
        self._restart_overhead = float(self.restart_overhead)
        # gap_seconds is on env
        self._gap_seconds = float(getattr(self.env, "gap_seconds", 0.0))
        self._initialized_env_params = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_env_params()

        # If we have already committed to on-demand, stay on it.
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        t = float(self.env.elapsed_seconds)
        gap = self._gap_seconds
        rem_need = self._task_duration  # Conservative: ignore completed work
        overhead = self._restart_overhead
        deadline = self._deadline

        # Check if it's still safe to spend one more gap on non-guaranteed work.
        # Worst case: next gap gives zero progress, then we pay one restart
        # overhead and run entirely on on-demand for the full task duration.
        can_explore = (t + gap + overhead + rem_need) <= deadline

        if not can_explore:
            # No more time to gamble on spot; commit to on-demand permanently.
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Exploration phase: use spot when available, otherwise pause (free).
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)