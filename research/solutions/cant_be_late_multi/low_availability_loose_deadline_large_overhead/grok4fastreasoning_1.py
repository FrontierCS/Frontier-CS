import json
from argparse import Namespace
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        self.num_regions = len(config["trace_files"])
        self.traces = []
        for tf in config["trace_files"]:
            with open(tf, 'r') as f:
                trace_data = json.load(f)
            trace = [bool(x) for x in trace_data]
            self.traces.append(trace)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done = sum(self.task_done_time)
        remain = self.task_duration - done
        if remain <= 0:
            return ClusterType.NONE

        s = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        t = int(s // gap)
        time_left = self.deadline - s
        pending = self.remaining_restart_overhead
        effective_time_left = time_left - pending

        current_r = self.env.get_current_region()
        is_rush = remain > 0.8 * effective_time_left

        if is_rush:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

        T = len(self.traces[0]) if self.traces else 0
        if t >= T:
            return ClusterType.ON_DEMAND

        candidates = []
        for r in range(self.num_regions):
            if t < len(self.traces[r]) and self.traces[r][t]:
                streak = 0
                for tt in range(t, len(self.traces[r])):
                    if self.traces[r][tt]:
                        streak += 1
                    else:
                        break
                candidates.append((streak, r))

        if candidates:
            def key_func(cand):
                streak, r = cand
                pref = 1 if r == current_r else 0
                dist = abs(r - current_r)
                return (streak, pref, -dist)
            best_cand = max(candidates, key=key_func)
            best_r = best_cand[1]
            if best_r != current_r:
                self.env.switch_region(best_r)
            return ClusterType.SPOT

        # no spot now, check for wait
        t_next = None
        for tt in range(t + 1, T):
            has_spot_tt = any(tt < len(self.traces[r]) and self.traces[r][tt] for r in range(self.num_regions))
            if has_spot_tt:
                t_next = tt
                break

        if t_next is None:
            return ClusterType.ON_DEMAND

        wait_time = (t_next - t) * gap
        if wait_time + remain > effective_time_left:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.NONE