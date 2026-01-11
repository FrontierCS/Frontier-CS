import json
import random
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_mr_v1"

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

        self._initialized = False
        self._work_done = 0.0
        self._last_task_list_len = 0

        # Safety guard to handle discretization and minor uncertainties.
        self._guard_seconds = None  # set after env is available

        # Commit flag: once ON_DEMAND is selected due to time pressure, stick with it.
        self._commit_to_od = False

        # Region statistics for adaptive multi-region behavior.
        # Each region tracks availability estimates and run-length stats.
        self._region_stats = {}
        self._cur_region_state = {}  # per region: last_state (bool or None), current_run_len
        self._last_region_index = None
        self._last_region_switch_time = 0.0
        self._scan_pointer = 0  # for round-robin scanning while waiting
        self._min_switch_interval = 0.0  # switching while idle is virtually free; allow as needed

        # Defaults for run-length estimates when no data.
        self._default_unavail_mean = None  # set after env init
        self._default_avail_mean = None

        # Stickiness: avoid flip-flop after choosing OD.
        self._od_started_time = None

        # Tie-breaking randomness
        random.seed(12345)

        return self

    def _ensure_initialized(self):
        if self._initialized:
            return
        num_regions = self.env.get_num_regions()
        for r in range(num_regions):
            self._region_stats[r] = {
                "total_time": 0.0,
                "avail_time": 0.0,
                "down_time": 0.0,
                # run-length stats
                "up_runs": 0,
                "down_runs": 0,
                "up_len_sum": 0.0,
                "down_len_sum": 0.0,
            }
            self._cur_region_state[r] = {
                "last_state": None,  # True (spot), False (no spot), None unknown
                "run_len": 0.0,
            }
        self._last_region_index = self.env.get_current_region()
        # Use environment parameters for defaults
        self._guard_seconds = max(2.0 * self.env.gap_seconds, min(600.0, 2.0 * self.restart_overhead))
        # Default unavailability mean based on overhead; choose moderately larger than overhead
        self._default_unavail_mean = max(2.0 * self.restart_overhead, 1800.0)  # at least 30 minutes
        self._default_avail_mean = 3600.0  # default 1 hour availability burst
        self._initialized = True

    def _update_work_done(self):
        # Incrementally update work done to avoid summing whole list each step.
        if self._last_task_list_len < len(self.task_done_time):
            new_segments = self.task_done_time[self._last_task_list_len:]
            for seg in new_segments:
                self._work_done += seg
            self._last_task_list_len = len(self.task_done_time)

    def _update_region_stats(self, region_idx: int, has_spot: bool):
        # Update per-region statistics based on current observation.
        rs = self._region_stats[region_idx]
        st = self._cur_region_state[region_idx]
        dt = self.env.gap_seconds

        rs["total_time"] += dt
        if has_spot:
            rs["avail_time"] += dt
        else:
            rs["down_time"] += dt

        # Update run-length stats for this region only for time spent in this region.
        last_state = st["last_state"]
        if last_state is None:
            st["last_state"] = has_spot
            st["run_len"] = dt
        else:
            if has_spot == last_state:
                st["run_len"] += dt
            else:
                # finalize previous run
                if last_state:
                    rs["up_runs"] += 1
                    rs["up_len_sum"] += st["run_len"]
                else:
                    rs["down_runs"] += 1
                    rs["down_len_sum"] += st["run_len"]
                # start new run
                st["last_state"] = has_spot
                st["run_len"] = dt

    def _estimate_unavail_remaining(self, region_idx: int) -> float:
        # Estimate residual unavailability duration for current region.
        rs = self._region_stats[region_idx]
        st = self._cur_region_state[region_idx]
        mean_unavail = (rs["down_len_sum"] / rs["down_runs"]) if rs["down_runs"] > 0 else self._default_unavail_mean
        # If we are currently in a down run in that region, estimate remaining as mean - elapsed
        cur_run_len = st["run_len"] if (st["last_state"] is False) else 0.0
        est = max(mean_unavail - cur_run_len, self.env.gap_seconds)
        return est

    def _region_score(self, region_idx: int) -> float:
        # Score for selecting region when scanning: smoothed availability ratio.
        rs = self._region_stats[region_idx]
        # Bayesian smoothing toward 0.5 to encourage exploration
        prior_total = 3600.0  # one hour prior
        prior_avail = 0.5 * prior_total
        total = rs["total_time"] + prior_total
        avail = rs["avail_time"] + prior_avail
        return avail / total

    def _pick_best_region(self, current_region: int) -> int:
        # Choose region with highest predicted availability score; tie-break randomly.
        num_regions = self.env.get_num_regions()
        best_score = -1.0
        candidates = []
        for r in range(num_regions):
            sc = self._region_score(r)
            if sc > best_score:
                best_score = sc
                candidates = [r]
            elif sc == best_score:
                candidates.append(r)
        if not candidates:
            return current_region
        # Prefer staying if current region is best among equals
        if current_region in candidates:
            return current_region
        return random.choice(candidates)

    def _round_robin_next_region(self, current_region: int) -> int:
        num_regions = self.env.get_num_regions()
        if num_regions <= 1:
            return current_region
        # Simple round-robin scanning to quickly cover regions while waiting
        nxt = (current_region + 1) % num_regions
        return nxt

    def _should_commit_to_od(self, last_cluster_type: ClusterType) -> bool:
        # Decide if we must start or stay on On-Demand to guarantee completion by deadline.
        time_left = self.deadline - self.env.elapsed_seconds
        remaining_work = max(self.task_duration - self._work_done, 0.0)
        overhead_needed = 0.0 if (last_cluster_type == ClusterType.ON_DEMAND) else self.restart_overhead
        # If we cannot afford to delay (consider guard), commit to OD.
        return time_left <= (overhead_needed + remaining_work + self._guard_seconds)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_initialized()
        self._update_work_done()

        # If work is complete, idle.
        remaining_work = max(self.task_duration - self._work_done, 0.0)
        if remaining_work <= 0:
            return ClusterType.NONE

        cur_region = self.env.get_current_region()

        # Update per-region stats for current observation.
        self._update_region_stats(cur_region, has_spot)

        # If we've previously committed to OD, keep using OD.
        if self._commit_to_od:
            return ClusterType.ON_DEMAND

        # Check if we must start or remain on OD to ensure meeting deadline.
        if self._should_commit_to_od(last_cluster_type):
            self._commit_to_od = True
            self._od_started_time = self.env.elapsed_seconds
            return ClusterType.ON_DEMAND

        # Not committed to OD yet; try to use Spot when available.
        if has_spot:
            # If we're currently on OD but not committed (rare), avoid churn: prefer continuing spot only if we have ample slack.
            # However, given we don't commit unless necessary, if has_spot true and we're not committed, use Spot.
            return ClusterType.SPOT

        # Spot unavailable: decide to wait (NONE) or switch to OD preemptively if slack is low.
        time_left = self.deadline - self.env.elapsed_seconds
        # Estimate remaining unavailability in this region
        est_unavail_remain = self._estimate_unavail_remaining(cur_region)

        # Maximum duration we can wait and still finish with OD later
        # If we wait wait_time seconds, then to finish with OD we need overhead + remaining_work.
        overhead_if_od_later = self.restart_overhead
        max_wait_allowed = time_left - (overhead_if_od_later + remaining_work) - self._guard_seconds

        if max_wait_allowed <= 0.0:
            # We cannot wait any longer; start OD now.
            self._commit_to_od = True
            self._od_started_time = self.env.elapsed_seconds
            return ClusterType.ON_DEMAND

        # If we can safely wait for expected spot return, do so.
        if est_unavail_remain <= max_wait_allowed:
            # While waiting, reposition to a promising region to catch spot sooner.
            best_region = self._pick_best_region(cur_region)
            # Also occasionally perform round-robin to explore undiscovered regions when data is sparse.
            if self._region_stats[best_region]["total_time"] < 600.0:
                # insufficient data: round-robin to explore quickly
                rr_region = self._round_robin_next_region(cur_region)
                # choose rr_region only if it hasn't been explored much more than best_region
                if self._region_stats[rr_region]["total_time"] < self._region_stats[best_region]["total_time"] + 1200.0:
                    best_region = rr_region

            if best_region != cur_region and (self.env.elapsed_seconds - self._last_region_switch_time >= self._min_switch_interval):
                self.env.switch_region(best_region)
                self._last_region_switch_time = self.env.elapsed_seconds

            return ClusterType.NONE

        # If expected wait is too long, but we still have enough slack to wait shorter than estimated:
        # Wait one more step if we have significant slack buffer; otherwise, commit to OD.
        # This provides some patience to catch transient spot returns without risking deadline.
        short_wait_buffer = min(self.env.gap_seconds * 3.0, max_wait_allowed)
        if short_wait_buffer > 0.0:
            # Reposition during short wait
            next_region = self._round_robin_next_region(cur_region)
            if next_region != cur_region and (self.env.elapsed_seconds - self._last_region_switch_time >= self._min_switch_interval):
                self.env.switch_region(next_region)
                self._last_region_switch_time = self.env.elapsed_seconds
            return ClusterType.NONE

        # No slack to wait; start OD now.
        self._commit_to_od = True
        self._od_started_time = self.env.elapsed_seconds
        return ClusterType.ON_DEMAND