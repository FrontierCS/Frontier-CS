from typing import Any, List, Tuple, Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_balanced"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        # Tunable parameters with sensible defaults
        self.cb_overhead_mult: float = getattr(args, 'cb_overhead_mult', 3.0) if args is not None else 3.0
        self.cb_gap_mult: float = getattr(args, 'cb_gap_mult', 3.0) if args is not None else 3.0
        self.cb_margin_minutes: float = getattr(args, 'cb_margin_minutes', 30.0) if args is not None else 30.0
        self.cb_max_margin_minutes: float = getattr(args, 'cb_max_margin_minutes', 180.0) if args is not None else 180.0
        self.commit_never_revert: bool = getattr(args, 'cb_commit_never_revert', True) if args is not None else True

        self.committed_to_od: bool = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _compute_done_seconds(self) -> float:
        done = 0.0
        segments = getattr(self, 'task_done_time', None)
        if not segments:
            return 0.0
        for seg in segments:
            try:
                if isinstance(seg, (list, tuple)):
                    if len(seg) >= 2:
                        s0 = float(seg[0])
                        s1 = float(seg[1])
                        done += max(0.0, s1 - s0)
                    elif len(seg) == 1:
                        done += max(0.0, float(seg[0]))
                elif isinstance(seg, dict):
                    if 'dur' in seg:
                        done += max(0.0, float(seg['dur']))
                    elif 'start' in seg and 'end' in seg:
                        s0 = float(seg['start'])
                        s1 = float(seg['end'])
                        done += max(0.0, s1 - s0)
                    else:
                        # Try best-effort on common keys
                        values = list(seg.values())
                        if len(values) >= 2:
                            done += max(0.0, float(values[1]) - float(values[0]))
                        elif len(values) == 1:
                            done += max(0.0, float(values[0]))
                else:
                    done += max(0.0, float(seg))
            except Exception:
                # Ignore malformed segments gracefully
                continue
        if hasattr(self, 'task_duration'):
            try:
                done = min(done, float(self.task_duration))
            except Exception:
                pass
        return max(0.0, done)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If task already done, do nothing
        done = self._compute_done_seconds()
        try:
            total = float(self.task_duration)
        except Exception:
            total = done  # Fallback to avoid negative if not available
        remaining = max(0.0, total - done)

        # If nothing left, choose NONE
        if remaining <= 0.0:
            return ClusterType.NONE

        # Environment-provided time context
        try:
            elapsed = float(self.env.elapsed_seconds)
        except Exception:
            elapsed = 0.0
        try:
            deadline = float(self.deadline)
        except Exception:
            deadline = elapsed + remaining  # Fallback: assume right amount of time left
        try:
            gap = float(self.env.gap_seconds)
        except Exception:
            gap = 300.0  # default 5 minutes
        try:
            overhead = float(self.restart_overhead)
        except Exception:
            overhead = 12.0 * 60.0  # default 12 minutes

        time_left = max(0.0, deadline - elapsed)
        slack = time_left - remaining

        # Compute conservative margin for committing to OD
        base_margin = self.cb_overhead_mult * overhead + self.cb_gap_mult * gap
        min_margin = max(0.0, float(self.cb_margin_minutes) * 60.0)
        max_margin = max(min_margin, float(self.cb_max_margin_minutes) * 60.0)
        margin = max(min_margin, base_margin)
        margin = min(margin, max_margin)

        # Commit condition: Once true, stick with OD to guarantee completion
        commit_condition = slack <= (overhead + margin)

        if not self.committed_to_od and commit_condition:
            self.committed_to_od = True

        if self.committed_to_od:
            return ClusterType.ON_DEMAND

        # Not committed to OD yet; opportunistically use Spot if available
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: wait if we still have sufficient slack; otherwise switch to OD
        if commit_condition:
            self.committed_to_od = True
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        try:
            parser.add_argument('--cb_overhead_mult', type=float, default=3.0)
            parser.add_argument('--cb_gap_mult', type=float, default=3.0)
            parser.add_argument('--cb_margin_minutes', type=float, default=30.0)
            parser.add_argument('--cb_max_margin_minutes', type=float, default=180.0)
            parser.add_argument('--cb_commit_never_revert', action='store_true', default=True)
        except Exception:
            pass
        args, _ = parser.parse_known_args()
        return cls(args)