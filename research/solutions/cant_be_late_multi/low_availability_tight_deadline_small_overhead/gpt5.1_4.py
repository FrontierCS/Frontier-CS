import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with slack-aware spot usage."""
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

        # Internal initialization flag; real init happens on first _step when env is ready.
        self._internal_initialized = False
        return self

    @staticmethod
    def _get_scalar(value):
        if isinstance(value, (list, tuple)):
            return value[0]
        return value

    def _init_internal_state(self):
        if getattr(self, "_internal_initialized", False):
            return

        # Core parameters in seconds
        self.task_duration_seconds = self._get_scalar(getattr(self, "task_duration", 0.0))
        self.deadline_seconds = self._get_scalar(getattr(self, "deadline", 0.0))
        self.restart_overhead_seconds = self._get_scalar(getattr(self, "restart_overhead", 0.0))

        # Work done tracking (incremental to avoid O(n^2) sums)
        task_done_list = getattr(self, "task_done_time", [])
        self._last_task_segments_count = len(task_done_list)
        work_done = 0.0
        for seg in task_done_list:
            work_done += seg
        self._work_done = work_done

        # Time tracking for per-cluster efficiency statistics
        self._prev_elapsed_seconds = getattr(self.env, "elapsed_seconds", 0.0)
        self._prev_work_done = self._work_done
        self._first_step = True

        # Spot efficiency tracking (global and per-region)
        self.spot_time_total = 0.0
        self.spot_work_total = 0.0
        self.spot_bad = False  # If True, we stop using spot entirely
        gap = getattr(self.env, "gap_seconds", 1.0) or 1.0
        # Require at least 1 hour of cumulative spot runtime before judging efficiency
        self.min_spot_eval_time = max(3600.0, 10.0 * gap)
        # Threshold: minimum effective utilization (work/time) for spot to be cost-effective
        # Using price ratio: p_spot/p_on_demand
        self.spot_eff_threshold = 0.9701 / 3.06  # ~0.317

        # Multi-region stats
        self.num_regions = self.env.get_num_regions() if hasattr(self.env, "get_num_regions") else 1
        self.region_total_steps = [0] * self.num_regions
        self.region_spot_steps = [0] * self.num_regions
        self.spot_time_per_region = [0.0] * self.num_regions
        self.spot_work_per_region = [0.0] * self.num_regions

        # Exploration parameters: limited fraction of horizon, aim ~15min/region
        max_steps = self.deadline_seconds / gap if self.deadline_seconds > 0 and gap > 0 else 0.0
        steps_upper_from_deadline = int(max_steps / (4.0 * self.num_regions)) if self.num_regions > 0 and max_steps > 0 else 0
        steps_from_time = int(900.0 / gap) if gap > 0 else 0  # 900s = 15 minutes
        if steps_upper_from_deadline <= 0:
            explore_steps_per_region = steps_from_time
        else:
            explore_steps_per_region = min(steps_from_time, steps_upper_from_deadline)
        if explore_steps_per_region <= 0:
            explore_steps_per_region = 1
        self.explore_steps_per_region = explore_steps_per_region
        self.exploration_done = (self.num_regions <= 1)
        self.explored_region_set = set()

        # Commit margin: buffer beyond theoretical latest safe start for ON_DEMAND
        self.commit_margin = max(3.0 * self.restart_overhead_seconds, 10.0 * gap)

        self._internal_initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not getattr(self, "_internal_initialized", False):
            self._init_internal_state()

        # Update incremental work done and per-cluster efficiency based on previous step
        current_time = self.env.elapsed_seconds
        delta_time = current_time - self._prev_elapsed_seconds

        # Incremental update of work done from new segments
        task_done_list = self.task_done_time
        curr_len = len(task_done_list)
        if curr_len > self._last_task_segments_count:
            new_total = 0.0
            for i in range(self._last_task_segments_count, curr_len):
                new_total += task_done_list[i]
            self._work_done += new_total
            self._last_task_segments_count = curr_len

        delta_work = self._work_done - self._prev_work_done

        # Region of the previous step is the current region now
        cur_region = self.env.get_current_region() if hasattr(self.env, "get_current_region") else 0

        # Update spot efficiency stats based on last step's action
        if not self._first_step and delta_time > 0.0:
            if last_cluster_type == ClusterType.SPOT:
                self.spot_time_total += delta_time
                if delta_work > 0.0:
                    self.spot_work_total += delta_work
                if 0 <= cur_region < self.num_regions:
                    self.spot_time_per_region[cur_region] += delta_time
                    if delta_work > 0.0:
                        self.spot_work_per_region[cur_region] += delta_work

        # Recompute previous markers for next step
        self._prev_elapsed_seconds = current_time
        self._prev_work_done = self._work_done
        self._first_step = False

        # Possibly mark spot as globally "bad" if too inefficient
        if (not self.spot_bad and
                self.spot_time_total >= self.min_spot_eval_time and
                self.spot_work_total > 0.0):
            eff = self.spot_work_total / self.spot_time_total  # in [0,1]
            if eff < self.spot_eff_threshold:
                self.spot_bad = True

        # If task already finished, run nothing
        if self._work_done >= self.task_duration_seconds - 1e-6:
            return ClusterType.NONE

        # Update region availability stats for current step (independent of action)
        if 0 <= cur_region < self.num_regions:
            self.region_total_steps[cur_region] += 1
            if has_spot:
                self.region_spot_steps[cur_region] += 1

        # Compute remaining work and slack vs deadline
        remaining_work = self.task_duration_seconds - self._work_done
        time_to_deadline = self.deadline_seconds - current_time
        slack_on_on_demand = time_to_deadline - (self.restart_overhead_seconds + remaining_work)

        # Choose cluster type for this step
        if time_to_deadline <= 0:
            cluster = ClusterType.ON_DEMAND
        elif slack_on_on_demand <= self.commit_margin:
            # Not enough slack left to take more risk: commit to ON_DEMAND
            cluster = ClusterType.ON_DEMAND
        else:
            # Plenty of slack; only use spot if available and not deemed cost-inefficient
            if has_spot and not self.spot_bad:
                cluster = ClusterType.SPOT
            else:
                # Idle when spot unavailable or globally bad; rely on future ON_DEMAND if needed
                cluster = ClusterType.NONE

        # Multi-region selection for future steps (only matters when we still use/seek spot)
        if self.num_regions > 1 and cluster != ClusterType.ON_DEMAND and not self.spot_bad:
            if not self.exploration_done:
                # Exploration: ensure each region gets at least explore_steps_per_region observations
                if self.region_total_steps[cur_region] >= self.explore_steps_per_region:
                    self.explored_region_set.add(cur_region)
                    if len(self.explored_region_set) >= self.num_regions:
                        self.exploration_done = True
                    else:
                        # Switch to next unexplored region
                        next_region = None
                        for idx in range(self.num_regions):
                            if idx not in self.explored_region_set:
                                next_region = idx
                                break
                        if next_region is not None and next_region != cur_region:
                            self.env.switch_region(next_region)
            else:
                # Exploitation: choose region with highest estimated spot availability
                alpha = 1.0
                beta = 1.0
                best_region = cur_region
                best_score = -1.0
                for idx in range(self.num_regions):
                    total = self.region_total_steps[idx]
                    spot_avail = self.region_spot_steps[idx]
                    score = (spot_avail + alpha) / (total + alpha + beta)
                    if score > best_score + 1e-12:
                        best_score = score
                        best_region = idx
                if best_region != cur_region:
                    self.env.switch_region(best_region)

        return cluster