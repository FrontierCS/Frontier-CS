import math
from typing import Any

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_deadline_guard_v1"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args
        self._od_locked = False

    def solve(self, spec_path: str) -> "Solution":
        self._od_locked = False
        return self

    def _done_seconds(self) -> float:
        td = getattr(self, "task_done", None)
        if isinstance(td, (int, float)):
            return float(td)

        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0

        if isinstance(tdt, (int, float)):
            return float(tdt)

        try:
            if hasattr(tdt, "__len__") and len(tdt) == 0:
                return 0.0
        except Exception:
            pass

        total = 0.0
        try:
            if isinstance(tdt, (list, tuple)):
                # If it looks like a cumulative time series, prefer last element.
                if all(isinstance(x, (int, float)) for x in tdt):
                    s = float(sum(tdt))
                    last = float(tdt[-1]) if tdt else 0.0
                    if len(tdt) >= 3 and all(tdt[i] <= tdt[i + 1] for i in range(len(tdt) - 1)):
                        if last > 0 and s > 1.5 * last:
                            return last
                    return s

                for seg in tdt:
                    if isinstance(seg, (int, float)):
                        total += float(seg)
                    elif isinstance(seg, (list, tuple)) and len(seg) == 2 and all(
                        isinstance(v, (int, float)) for v in seg
                    ):
                        total += float(seg[1] - seg[0])
                    elif isinstance(seg, dict):
                        if "duration" in seg and isinstance(seg["duration"], (int, float)):
                            total += float(seg["duration"])
                        elif "done" in seg and isinstance(seg["done"], (int, float)):
                            total += float(seg["done"])
                return total
        except Exception:
            return 0.0

        return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        g = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if g <= 0:
            g = 60.0

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        T = deadline - elapsed

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        done = self._done_seconds()
        if done < 0:
            done = 0.0
        if task_duration > 0:
            done = min(done, task_duration)
        R = max(0.0, task_duration - done)

        if R <= 0.0:
            return ClusterType.NONE

        if T <= 0.0:
            return ClusterType.ON_DEMAND

        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        # Once we start on-demand, never switch away (avoid extra overhead and risk).
        if self._od_locked or last_cluster_type == ClusterType.ON_DEMAND:
            self._od_locked = True
            return ClusterType.ON_DEMAND

        safety = min(g, 300.0)  # conservative guard against step discretization

        def overhead_to_start(target: ClusterType) -> float:
            if target == ClusterType.NONE:
                return 0.0
            return 0.0 if last_cluster_type == target else restart_overhead

        # If spot is available, prefer SPOT if it remains feasible under worst-case:
        # after this step, spot disappears permanently and we must finish on on-demand.
        if has_spot:
            oh_spot = overhead_to_start(ClusterType.SPOT)
            prog_spot = max(0.0, g - oh_spot)
            R_after = max(0.0, R - prog_spot)

            if R_after <= 0.0:
                return ClusterType.SPOT

            required_if_spot_then_od = g + restart_overhead + R_after + safety
            if required_if_spot_then_od <= T + 1e-9:
                return ClusterType.SPOT

            self._od_locked = True
            return ClusterType.ON_DEMAND

        # No spot: prefer waiting (NONE) if still feasible; otherwise start on-demand.
        required_if_wait_then_od = g + restart_overhead + R + safety
        if required_if_wait_then_od <= T + 1e-9:
            return ClusterType.NONE

        self._od_locked = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
