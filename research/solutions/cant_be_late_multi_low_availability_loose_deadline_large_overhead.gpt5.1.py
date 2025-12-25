import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with deadline guarantee and cost awareness."""

    NAME = "cbl_multi_region_strategy"

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

        # Persistent state for statistics and control
        self.prev_elapsed_seconds = 0.0
        self.prev_work_done = 0.0

        self.spot_time = 0.0
        self.spot_work = 0.0
        self.od_time = 0.0
        self.od_work = 0.0
        self.idle_time = 0.0

        self.committed_to_on_demand = False

        # Heuristic parameters
        gap = getattr(self.env, "gap_seconds", 60.0)
        restart_overhead = self._get_restart_overhead()

        # Extra safety margin beyond the theoretical OD-only time
        self.commit_margin = 3.0 * gap + 2.0 * restart_overhead

        # Cost parameters (from problem statement)
        self.spot_cost_per_hour = 0.9701
        self.on_demand_cost_per_hour = 3.06
        # Minimum effective spot throughput (fraction of wall time) to be cost-effective
        self.cost_ratio_threshold = self.spot_cost_per_hour / self.on_demand_cost_per_hour

        # Require some minimum observation time on spot before trusting its estimate
        self.min_spot_observation_time = 6.0 * gap

        return self

    def _get_task_duration(self) -> float:
        td = getattr(self, "task_duration", None)
        if isinstance(td, (list, tuple)):
            return float(td[0])
        return float(td)

    def _get_restart_overhead(self) -> float:
        ro = getattr(self, "restart_overhead", None)
        if isinstance(ro, (list, tuple)):
            return float(ro[0])
        return float(ro)

    def _update_stats(self, last_cluster_type: ClusterType) -> None:
        """Update internal statistics based on progress since last step."""
        t = float(self.env.elapsed_seconds)
        work_done = float(sum(self.task_done_time))

        delta_t = t - self.prev_elapsed_seconds
        delta_w = work_done - self.prev_work_done

        if delta_t < 0:
            delta_t = 0.0
        if delta_w < 0:
            delta_w = 0.0

        if last_cluster_type == ClusterType.SPOT:
            self.spot_time += delta_t
            self.spot_work += delta_w
        elif last_cluster_type == ClusterType.ON_DEMAND:
            self.od_time += delta_t
            self.od_work += delta_w
        else:
            # Treat NONE or unknown as idle time
            self.idle_time += delta_t

        self.prev_elapsed_seconds = t
        self.prev_work_done = work_done

    def _estimate_spot_rate(self) -> float:
        """Return estimated effective spot throughput (work / elapsed time)."""
        if self.spot_time <= 0.0:
            return None
        return self.spot_work / self.spot_time

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update stats based on what happened in the last step
        self._update_stats(last_cluster_type)

        # Basic quantities
        t = float(self.env.elapsed_seconds)
        deadline = float(self.deadline)
        gap = float(self.env.gap_seconds)

        total_duration = self._get_task_duration()
        work_done = float(sum(self.task_done_time))
        remaining_work = max(0.0, total_duration - work_done)

        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = deadline - t
        if time_left <= 0.0:
            # Already at or past deadline; nothing we do now can help
            return ClusterType.NONE

        restart_overhead = self._get_restart_overhead()

        # Estimate spot performance
        spot_rate = self._estimate_spot_rate()
        spot_bad = False
        if (
            spot_rate is not None
            and self.spot_time >= self.min_spot_observation_time
        ):
            # Spot is not cost-effective if effective throughput too low
            min_good_rate = max(0.1, self.cost_ratio_threshold * 1.1)
            if spot_rate < min_good_rate:
                spot_bad = True

        # Time needed if we switch to OD now and never leave it again
        safe_od_time = remaining_work + restart_overhead

        # Decide whether we must commit to on-demand to safely finish
        if not self.committed_to_on_demand:
            if time_left <= safe_od_time + self.commit_margin:
                # From now on, always use on-demand to avoid missing the deadline
                self.committed_to_on_demand = True

        if self.committed_to_on_demand:
            return ClusterType.ON_DEMAND

        # We still have sufficient slack to use spot or wait.
        extra_slack = time_left - (safe_od_time + self.commit_margin)

        # Prefer spot when available and not clearly bad.
        if has_spot and not spot_bad:
            return ClusterType.SPOT

        # No spot (or it's bad). Decide between waiting and early OD.
        # If we can afford to waste one more gap of time and still have
        # (safe_od_time + commit_margin) left, we can wait; otherwise, use OD.
        if extra_slack > gap:
            return ClusterType.NONE

        # Not enough slack left to keep waiting; commit to OD from now on.
        self.committed_to_on_demand = True
        return ClusterType.ON_DEMAND
