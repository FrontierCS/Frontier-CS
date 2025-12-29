import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Load spot availability traces
        self.spot_avail = []
        for trace_file in config["trace_files"]:
            with open(trace_file) as tf:
                # Assume each line is 0 or 1
                lines = [line.strip() for line in tf if line.strip()]
                avail = [bool(int(line)) for line in lines]
                self.spot_avail.append(avail)

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        g = self.env.gap_seconds
        current_region = self.env.get_current_region()
        t = int(self.env.elapsed_seconds / g)

        # Safety: if trace index out of range, treat as no spot
        def spot_avail(region, step):
            if (region < len(self.spot_avail) and
                step < len(self.spot_avail[region])):
                return self.spot_avail[region][step]
            return False

        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE

        remaining_time = self.deadline - self.env.elapsed_seconds
        remaining_steps = int(remaining_time / g)
        if remaining_steps <= 0:
            return ClusterType.NONE

        # Critical condition: must maximize work per step
        if remaining_work > remaining_steps * g * 0.8:
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND

        # Non-critical: try to use spot
        current_has_spot = spot_avail(current_region, t)
        if current_has_spot:
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            else:
                if remaining_steps * g - remaining_work > self.restart_overhead:
                    return ClusterType.SPOT
                else:
                    if last_cluster_type == ClusterType.ON_DEMAND:
                        return ClusterType.ON_DEMAND
                    else:
                        return ClusterType.ON_DEMAND
        else:
            # Look for a region with good consecutive spot availability
            best_region = current_region
            best_consecutive = 0
            num_regions = self.env.get_num_regions()
            for r in range(num_regions):
                if spot_avail(r, t):
                    consec = 0
                    for s in range(t, min(t + 5, len(self.spot_avail[r]))):
                        if spot_avail(r, s):
                            consec += 1
                        else:
                            break
                    if consec > best_consecutive:
                        best_consecutive = consec
                        best_region = r

            if best_consecutive >= 2:
                if best_region != current_region:
                    self.env.switch_region(best_region)
                if remaining_steps * g - remaining_work > self.restart_overhead:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                # Consider pausing if spot appears soon
                earliest_spot = None
                max_lookahead = min(10, len(self.spot_avail[0]) - t - 1 if self.spot_avail else 0)
                for s in range(t + 1, t + max_lookahead + 1):
                    for r in range(num_regions):
                        if spot_avail(r, s):
                            earliest_spot = s
                            break
                    if earliest_spot is not None:
                        break

                if (earliest_spot is not None and
                    (earliest_spot - t) * g <= remaining_time - remaining_work):
                    return ClusterType.NONE
                else:
                    return ClusterType.ON_DEMAND