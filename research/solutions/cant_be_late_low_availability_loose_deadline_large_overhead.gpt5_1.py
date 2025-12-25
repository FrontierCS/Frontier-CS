import os
import json
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_wait_commit_v2"

    def __init__(self, args=None):
        super().__init__(args)
        # Once committed to on-demand, never switch back
        self._committed_to_od = False
        # Tuning parameters (can be overridden via args or spec)
        self._commit_gap_mult = 2.0  # commit threshold includes this many gap_seconds
        self._extra_margin_seconds = 0.0

    def solve(self, spec_path: str) -> "Solution":
        # Optionally load a simple JSON config with keys: commit_gap_mult, extra_margin_seconds
        try:
            if spec_path and os.path.exists(spec_path):
                with open(spec_path, "r") as f:
                    txt = f.read().strip()
                if txt:
                    try:
                        cfg = json.loads(txt)
                        if isinstance(cfg, dict):
                            if "commit_gap_mult" in cfg:
                                self._commit_gap_mult = float(cfg["commit_gap_mult"])
                            if "extra_margin_seconds" in cfg:
                                self._extra_margin_seconds = float(cfg["extra_margin_seconds"])
                    except Exception:
                        pass
        except Exception:
            pass
        return self

    def _remaining_work(self) -> float:
        done = 0.0
        try:
            if isinstance(self.task_done_time, (list, tuple)):
                done = float(sum(self.task_done_time))
            else:
                done = float(self.task_done_time)
        except Exception:
            done = 0.0
        rem = self.task_duration - done
        return rem if rem > 0.0 else 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we've already committed to on-demand, stay there.
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        gap = float(self.env.gap_seconds)
        R = float(self.restart_overhead)

        remaining = self._remaining_work()
        if remaining <= 0.0:
            # Task finished; do nothing to avoid unnecessary costs
            self._committed_to_od = True
            return ClusterType.NONE

        time_left = float(self.deadline - self.env.elapsed_seconds)
        # Slack: how much we can afford to wait or lose (not doing real work)
        slack = time_left - remaining

        # Commit threshold accounts for one restart overhead plus some margin for discretization
        commit_threshold = R + self._commit_gap_mult * gap + self._extra_margin_seconds

        # Safety: if slack at or below threshold, we must run on-demand now to guarantee finish
        if slack <= commit_threshold:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, we can still gamble on spot:
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: wait if we can afford at least one more step, else commit to on-demand
        if slack - gap >= commit_threshold:
            return ClusterType.NONE

        # Not enough slack to wait even one step; commit to on-demand immediately.
        self._committed_to_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        try:
            parser.add_argument("--commit_gap_mult", type=float, default=2.0)
            parser.add_argument("--extra_margin_seconds", type=float, default=0.0)
        except Exception:
            pass
        args, _ = parser.parse_known_args()
        inst = cls(args)
        try:
            inst._commit_gap_mult = float(getattr(args, "commit_gap_mult", 2.0))
            inst._extra_margin_seconds = float(getattr(args, "extra_margin_seconds", 0.0))
        except Exception:
            pass
        return inst