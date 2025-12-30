import math
from collections import deque

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:
    from enum import Enum

    class ClusterType(Enum):
        SPOT = "spot"
        ON_DEMAND = "on_demand"
        NONE = "none"

    class Strategy:
        def __init__(self, *args, **kwargs):
            self.env = None


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._alpha = 2.0
        self._beta = 2.0

        self._spot_hist = deque(maxlen=256)
        self._last_has_spot = None

        self._consec_spot = 0
        self._consec_no_spot = 0

        self._committed_od = False
        self._od_started_time = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _work_done_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0
        if isinstance(tdt, (int, float)):
            return float(tdt)

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)

        if isinstance(tdt, list):
            if not tdt:
                return 0.0

            # List of numeric values: could be segment durations or cumulative progress.
            if all(isinstance(x, (int, float)) for x in tdt):
                vals = [float(x) for x in tdt]
                s = float(sum(vals))
                last = float(vals[-1])
                nondecreasing = True
                for i in range(len(vals) - 1):
                    if vals[i] > vals[i + 1] + 1e-12:
                        nondecreasing = False
                        break
                if nondecreasing and task_duration > 0.0 and last <= task_duration + 1e-6 and s > last * 1.5:
                    done = last
                else:
                    done = s
                if task_duration > 0.0:
                    done = min(done, task_duration)
                return max(0.0, done)

            # List of tuples/lists (start, end) or dicts
            total = 0.0
            for x in tdt:
                if isinstance(x, (tuple, list)) and len(x) >= 2 and isinstance(x[0], (int, float)) and isinstance(x[1], (int, float)):
                    total += float(x[1]) - float(x[0])
                elif isinstance(x, dict):
                    if "duration" in x and isinstance(x["duration"], (int, float)):
                        total += float(x["duration"])
                    elif "start" in x and "end" in x and isinstance(x["start"], (int, float)) and isinstance(x["end"], (int, float)):
                        total += float(x["end"]) - float(x["start"])
            if task_duration > 0.0:
                total = min(total, task_duration)
            return max(0.0, total)

        return 0.0

    def _spot_stats(self):
        n = self._alpha + self._beta
        p_mean = self._alpha / n if n > 0 else 0.5
        stderr = math.sqrt(max(0.0, p_mean * (1.0 - p_mean) / (n + 1.0)))
        # Conservative lower bound
        p_low = p_mean - 1.0 * stderr - 0.05
        p_low = min(0.98, max(0.05, p_low))

        if len(self._spot_hist) >= 2:
            trans = 0
            prev = self._spot_hist[0]
            for v in list(self._spot_hist)[1:]:
                if v != prev:
                    trans += 1
                prev = v
            trans_rate = trans / (len(self._spot_hist) - 1)
        else:
            trans_rate = 0.0

        return p_mean, p_low, trans_rate

    def _choose_od(self, elapsed: float, last_cluster_type: ClusterType) -> ClusterType:
        if last_cluster_type != ClusterType.ON_DEMAND:
            self._od_started_time = elapsed
        return ClusterType.ON_DEMAND

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = getattr(self, "env", None)
        elapsed = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(env, "gap_seconds", 1.0) or 1.0)

        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        time_remaining = max(0.0, deadline - elapsed)
        done = self._work_done_seconds()
        remaining_work = max(0.0, task_duration - done)

        if remaining_work <= 1e-9:
            return ClusterType.NONE

        # Update availability stats
        if has_spot:
            self._alpha += 1.0
        else:
            self._beta += 1.0

        if self._last_has_spot is not None:
            self._spot_hist.append(has_spot)
        else:
            self._spot_hist.append(has_spot)
        self._last_has_spot = has_spot

        if has_spot:
            self._consec_spot += 1
            self._consec_no_spot = 0
        else:
            self._consec_no_spot += 1
            self._consec_spot = 0

        p_mean, p_low, trans_rate = self._spot_stats()

        # Expected future overhead if we follow "SPOT when available else OD" behavior
        steps_remaining = time_remaining / max(gap, 1e-9)
        expected_switches = trans_rate * steps_remaining
        overhead_expected = expected_switches * restart_overhead
        overhead_expected = min(overhead_expected, 0.5 * time_remaining)

        # Safety: if we went OD now and stayed there, can we still make it?
        od_start_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead
        min_time_to_finish_od = remaining_work + od_start_overhead

        # Commit-to-OD conditions
        slack = time_remaining - remaining_work
        if not self._committed_od:
            if time_remaining <= 0.0:
                self._committed_od = True
            elif min_time_to_finish_od >= time_remaining - 0.5 * gap:
                self._committed_od = True
            else:
                req_rate = (remaining_work + overhead_expected) / max(time_remaining, 1e-9)
                if req_rate >= 0.98:
                    self._committed_od = True
                elif slack <= 1.5 * restart_overhead:
                    self._committed_od = True

        if self._committed_od:
            return self._choose_od(elapsed, last_cluster_type)

        # Pressure to run OD during unavailability (conservative planning)
        unavail_est = (1.0 - p_low) * time_remaining
        deficit = (remaining_work + overhead_expected) - p_low * time_remaining
        if unavail_est > 1e-9:
            od_pressure = max(0.0, deficit) / unavail_est
        else:
            od_pressure = 1.0 if deficit > 0.0 else 0.0
        od_pressure = min(1.0, max(0.0, od_pressure))

        # If already on OD, avoid stopping (prevents extra overhead churn)
        if last_cluster_type == ClusterType.ON_DEMAND:
            if has_spot:
                min_od_runtime = max(2.0 * restart_overhead, 2.0 * gap)
                if self._od_started_time is not None and (elapsed - self._od_started_time) < min_od_runtime:
                    return ClusterType.ON_DEMAND
                if slack <= 2.5 * restart_overhead:
                    return ClusterType.ON_DEMAND
                if od_pressure > 0.85 and p_mean < 0.8:
                    return ClusterType.ON_DEMAND
                if self._consec_spot < 2:
                    return ClusterType.ON_DEMAND
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        # No spot and not currently on OD: decide OD vs NONE
        if time_remaining <= remaining_work + restart_overhead + gap:
            return self._choose_od(elapsed, last_cluster_type)

        patience_seconds = max(2.0 * restart_overhead, 2.0 * gap)
        patience_steps = max(1, int(math.ceil(patience_seconds / max(gap, 1e-9))))

        # If we likely don't need OD and we have slack, wait for spot
        if od_pressure <= 0.05 and slack > 4.0 * gap:
            return ClusterType.NONE

        # For mild OD pressure, wait a bit to avoid churn on short outages
        if self._consec_no_spot < patience_steps and od_pressure < 0.6 and slack > 6.0 * gap:
            return ClusterType.NONE

        return self._choose_od(elapsed, last_cluster_type)

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)