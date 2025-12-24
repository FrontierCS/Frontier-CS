from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_threshold_od_lock_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self.lock_on_demand = False
        self.guard_gap_multiplier = getattr(args, "guard_gap_multiplier", 1.0) if args is not None else 1.0
        self.extra_guard_fraction_of_restart = getattr(args, "extra_guard_fraction", 0.05) if args is not None else 0.05
        self.initialized = False

    def solve(self, spec_path: str):
        self.initialized = True
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = self.env
        t = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(env, "gap_seconds", 60.0) or 60.0)
        restart = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", float("inf")) or float("inf"))
        total = float(getattr(self, "task_duration", 0.0) or 0.0)

        # Compute done work
        done = 0.0
        try:
            tdt = getattr(self, "task_done_time", None)
            if isinstance(tdt, (list, tuple)):
                done = float(sum(tdt))
            elif tdt is not None:
                done = float(tdt)
        except Exception:
            done = 0.0

        remaining_work = max(total - done, 0.0)
        if remaining_work <= 1e-9:
            self.lock_on_demand = False
            return ClusterType.NONE

        remaining_time = max(deadline - t, 0.0)
        guard = self.guard_gap_multiplier * gap + self.extra_guard_fraction_of_restart * restart

        # If even switching to OD now wouldn't be enough, still choose OD (best effort).
        overhead_if_switch_now = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart
        if remaining_work + overhead_if_switch_now > remaining_time - 1e-9:
            self.lock_on_demand = True
            return ClusterType.ON_DEMAND

        # Latest time to start OD (accounting for one restart overhead).
        latest_start_with_one_restart = deadline - (remaining_work + restart)

        if not self.lock_on_demand and (t + guard >= latest_start_with_one_restart):
            self.lock_on_demand = True

        if self.lock_on_demand:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: wait if safely before latest start; otherwise switch to OD and lock.
        if t + guard < latest_start_with_one_restart:
            return ClusterType.NONE
        else:
            self.lock_on_demand = True
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        try:
            parser.add_argument("--guard_gap_multiplier", type=float, default=1.0)
            parser.add_argument("--extra_guard_fraction", type=float, default=0.05)
        except Exception:
            pass
        args, _ = parser.parse_known_args()
        return cls(args)
