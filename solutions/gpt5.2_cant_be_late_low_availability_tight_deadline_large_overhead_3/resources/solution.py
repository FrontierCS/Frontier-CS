import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self._reset_state()

    def _reset_state(self) -> None:
        self._committed_od = False

        self._last_elapsed: Optional[float] = None

        self._has_spot_prev: Optional[bool] = None
        self._avail_streak = 0
        self._unavail_streak = 0

        self._burst_count = 0
        self._avg_burst_steps = 0.0  # running mean of consecutive-availability lengths (in steps)

        self._k_over = None
        self._guard = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _work_done_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0
        if isinstance(tdt, (int, float)):
            return float(tdt)

        if not isinstance(tdt, (list, tuple)) or len(tdt) == 0:
            return 0.0

        # If entries are (start, end) segments
        seg_sum = 0.0
        numeric_vals = []
        has_pair = False

        for x in tdt:
            if isinstance(x, (list, tuple)) and len(x) >= 2 and isinstance(x[0], (int, float)) and isinstance(x[1], (int, float)):
                has_pair = True
                a = float(x[0])
                b = float(x[1])
                if b > a:
                    seg_sum += (b - a)
            elif isinstance(x, (int, float)):
                numeric_vals.append(float(x))

        if has_pair:
            done = seg_sum
        elif numeric_vals:
            # Detect cumulative list vs per-segment durations.
            is_monotone = True
            for i in range(len(numeric_vals) - 1):
                if numeric_vals[i + 1] + 1e-9 < numeric_vals[i]:
                    is_monotone = False
                    break

            if is_monotone:
                last = numeric_vals[-1]
                s = sum(numeric_vals)
                # If it looks cumulative, use the last value.
                if last >= 0.0 and s > 2.0 * max(last, 1e-9):
                    done = last
                else:
                    done = s
            else:
                done = sum(numeric_vals)
        else:
            done = 0.0

        td = float(getattr(self, "task_duration", 0.0) or 0.0)
        if td > 0.0:
            if done < 0.0:
                done = 0.0
            elif done > td:
                done = td
        return done

    def _update_spot_stats(self, has_spot: bool) -> None:
        if self._has_spot_prev is None:
            self._has_spot_prev = has_spot
            self._avail_streak = 1 if has_spot else 0
            self._unavail_streak = 0 if has_spot else 1
            return

        if has_spot:
            if self._has_spot_prev:
                self._avail_streak += 1
            else:
                self._avail_streak = 1
            self._unavail_streak = 0
        else:
            if self._has_spot_prev:
                # availability burst just ended; record burst length
                burst_len = self._avail_streak
                if burst_len > 0:
                    self._burst_count += 1
                    if self._burst_count == 1:
                        self._avg_burst_steps = float(burst_len)
                    else:
                        self._avg_burst_steps += (float(burst_len) - self._avg_burst_steps) / float(self._burst_count)
                self._avail_streak = 0

            if not self._has_spot_prev:
                self._unavail_streak += 1
            else:
                self._unavail_streak = 1

        self._has_spot_prev = has_spot

    def _probe_steps(self) -> int:
        # 0/1/2 steps of "wait for confirmation" when spot just becomes available.
        # Only enabled when observed bursts are typically short relative to restart overhead.
        if self._k_over is None:
            return 0
        if self._burst_count < 5:
            return 0

        avg = self._avg_burst_steps
        k = int(self._k_over)

        if avg <= k + 0.5:
            return min(2, max(0, k - 1))
        if avg <= 2.0 * k:
            return 1
        return 0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = float(self.env.elapsed_seconds)

        if self._last_elapsed is None or elapsed + 1e-9 < self._last_elapsed:
            self._reset_state()
        self._last_elapsed = elapsed

        gap = float(self.env.gap_seconds)
        if self._guard is None:
            self._guard = max(2.0 * gap, 1.0)
        if self._k_over is None:
            ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
            self._k_over = int(max(1, math.ceil(ro / max(gap, 1e-9)))) if ro > 0.0 else 1

        self._update_spot_stats(has_spot)

        done = self._work_done_seconds()
        td = float(getattr(self, "task_duration", 0.0) or 0.0)
        if td <= 0.0:
            return ClusterType.NONE

        work_left = max(0.0, td - done)
        if work_left <= 1e-6:
            self._committed_od = False
            return ClusterType.NONE

        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        guard = float(self._guard)

        time_left = deadline - elapsed
        slack = time_left - work_left

        if last_cluster_type == ClusterType.ON_DEMAND:
            self._committed_od = True

        if self._committed_od:
            return ClusterType.ON_DEMAND

        # Commit to on-demand when we can no longer tolerate a restart overhead (spot loss) and still meet deadline.
        if slack <= ro + guard:
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # If we are already running spot and it's available, keep using it.
        if has_spot and last_cluster_type == ClusterType.SPOT:
            return ClusterType.SPOT

        # If spot is available, typically use it.
        if has_spot:
            # Optional short probing when bursts are typically too short to amortize overhead, but only when we have ample slack.
            psteps = self._probe_steps()
            if (
                psteps > 0
                and last_cluster_type != ClusterType.SPOT
                and self._avail_streak <= psteps
                and slack > (2.0 * ro + guard)
            ):
                return ClusterType.NONE
            return ClusterType.SPOT

        # Spot unavailable: pause unless we're close enough to the deadline to require on-demand (handled above).
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
