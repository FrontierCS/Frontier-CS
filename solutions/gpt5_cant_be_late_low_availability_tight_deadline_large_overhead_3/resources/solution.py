import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "jitt_od_lazy_v2"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass
        self._committed_to_od = False
        self._last_reset_time = -1.0
        # Optional user tunables
        self._user_margin_minutes = getattr(args, "margin_minutes", None) if args is not None else None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work(self) -> float:
        done = 0.0
        try:
            # task_done_time is a list of completed work segments
            done = float(sum(self.task_done_time)) if self.task_done_time is not None else 0.0
        except Exception:
            done = 0.0
        rem = float(self.task_duration) - done
        if rem < 0:
            rem = 0.0
        return rem

    def _safety_time(self, dt: float) -> float:
        if self._user_margin_minutes is not None:
            return max(1.0, float(self._user_margin_minutes) * 60.0)
        # Ensure we commit before threshold by at least one step plus small cushion
        return max(dt + 120.0, 1.0)

    def _should_commit_now(self, now: float, dt: float) -> bool:
        # Compute if we must switch to On-Demand now to guarantee finishing by the deadline.
        rem_work = self._remaining_work()
        if rem_work <= 0.0:
            return False
        # If already on on-demand, no additional overhead needed to continue.
        # Otherwise, we conservatively include one restart overhead in commitment calculation.
        overhead = 0.0 if self.env.cluster_type == ClusterType.ON_DEMAND or self._committed_to_od else float(self.restart_overhead)
        safety = self._safety_time(dt)
        latest_start_time = float(self.deadline) - (rem_work + overhead + safety)
        return now >= latest_start_time

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        now = float(self.env.elapsed_seconds)
        dt = float(self.env.gap_seconds)

        # Reset per-episode state at the start of each new run
        if now <= 1e-9 or self._last_reset_time > now:
            self._committed_to_od = False
            self._last_reset_time = now
        else:
            self._last_reset_time = now

        # If task already complete, do nothing.
        rem_work = self._remaining_work()
        if rem_work <= 0.0:
            return ClusterType.NONE

        # If we already committed to on-demand, stay on OD to avoid extra overhead/risk.
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Decide whether we must commit now to guarantee deadline.
        if self._should_commit_now(now, dt):
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, use Spot if available; else wait (NONE) to save cost until commit time.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        # Optional custom arguments
        parser.add_argument("--margin-minutes", type=float, default=None, help="Extra safety minutes before commit.")
        args, _ = parser.parse_known_args()
        return cls(args)
