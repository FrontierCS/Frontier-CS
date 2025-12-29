import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_slack_mr_v1"

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
        # Internal initialization
        self._initialized = False
        return self

    # Helpers
    def _ensure_init(self):
        if self._initialized:
            return
        n = self.env.get_num_regions()
        self._num_regions = n
        # Per-region stats
        self._region_obs = [0] * n
        self._region_spot_true = [0] * n
        self._region_streak = [0] * n
        self._initialized = True

    def _total_task_duration(self):
        td = self.task_duration
        if isinstance(td, (list, tuple)):
            return float(sum(td))
        return float(td)

    def _remaining_work(self):
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        return max(0.0, self._total_task_duration() - done)

    def _update_region_stats(self, region_idx: int, has_spot: bool):
        self._region_obs[region_idx] += 1
        if has_spot:
            self._region_spot_true[region_idx] += 1
            self._region_streak[region_idx] += 1
        else:
            self._region_streak[region_idx] = 0

    def _region_score(self, idx: int):
        # Laplace smoothing + mild bonus for recent streak
        obs = self._region_obs[idx]
        trues = self._region_spot_true[idx]
        rate = (trues + 1.0) / (obs + 2.0)
        streak_bonus = 0.05 * min(self._region_streak[idx], 20)
        return rate + streak_bonus

    def _pick_best_region(self, current_idx: int):
        # Choose region with highest score
        best = current_idx
        best_score = self._region_score(current_idx)
        for i in range(self._num_regions):
            sc = self._region_score(i)
            if sc > best_score + 1e-12 or (abs(sc - best_score) <= 1e-12 and i < best):
                best = i
                best_score = sc
        return best

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()

        # Update region stats with current observation
        cur_region = self.env.get_current_region()
        self._update_region_stats(cur_region, has_spot)

        # Basic parameters
        gap = float(self.env.gap_seconds)
        t_left = float(self.deadline - self.env.elapsed_seconds)
        rem = self._remaining_work()
        if rem <= 0.0:
            return ClusterType.NONE

        # Safety margin: conservative but not too large
        # Ensures we have buffer for rounding/overhead uncertainty
        margin = max(2.0 * float(self.restart_overhead), 0.2 * gap)

        # If already on OD, keep it (avoid extra overhead/switching)
        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        # Compute whether we must commit to OD now
        # Time needed to finish on OD if we start OD now
        # If already in OD (handled above), needed = remaining_restart_overhead + rem
        # Else switching to OD: overhead + rem
        t_need_od_now = float(self.restart_overhead) + rem

        # Panic: if not enough time left, go OD immediately
        if t_left <= t_need_od_now + margin:
            return ClusterType.ON_DEMAND

        # We have enough slack to consider Spot/None
        # Decide action for this step with worst-case bounds to guarantee feasibility
        if has_spot:
            # If last cluster already Spot: no new launch overhead this step
            if last_cluster_type == ClusterType.SPOT:
                # Safe to run one more Spot step only if after spending one gap, we can still finish with OD
                if (t_left - gap) >= (rem + float(self.restart_overhead) + margin):
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                # Launching new Spot instance incurs overhead for this step as well
                # Worst-case this step costs gap + restart_overhead in time, then OD next
                if (t_left - (gap + float(self.restart_overhead))) >= (rem + float(self.restart_overhead) + margin):
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
        else:
            # Spot not available now
            # We can wait (NONE) only if after one gap we can still finish with OD
            if (t_left - gap) >= (rem + float(self.restart_overhead) + margin):
                # While waiting, move to the best region to increase chances next step
                best_region = self._pick_best_region(cur_region)
                if best_region != cur_region:
                    self.env.switch_region(best_region)
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND