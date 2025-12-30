import json
from argparse import Namespace
from typing import List, Optional
import math
import random

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v1"

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

        # Internal state (lazy init in _step in case env not ready here)
        self._initialized = False
        self._od_locked = False
        self._last_region = None
        self._last_has_spot = None

        # Per-region statistics
        self._num_regions = None
        self._ema_avail: List[float] = []
        self._seen_count: List[int] = []
        self._spot_count: List[int] = []
        self._uptime_streak: List[int] = []
        self._downtime_streak: List[int] = []
        self._cooldown_until: List[float] = []
        self._last_observed_time: List[float] = []

        # Scanning state
        self._last_scan_switch_time: float = 0.0
        self._scan_step_interval: int = 1  # steps to stay before switching during scanning
        self._scan_step_counter: int = 0

        # Random seed for tie-breaking
        self._rng = random.Random(12345)

        return self

    # ------------- Helpers -------------
    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        try:
            n = self.env.get_num_regions()
        except Exception:
            n = 1
        self._num_regions = n
        self._ema_avail = [0.6 for _ in range(n)]
        self._seen_count = [0 for _ in range(n)]
        self._spot_count = [0 for _ in range(n)]
        self._uptime_streak = [0 for _ in range(n)]
        self._downtime_streak = [0 for _ in range(n)]
        self._cooldown_until = [0.0 for _ in range(n)]
        self._last_observed_time = [0.0 for _ in range(n)]
        self._initialized = True

    def _time_now(self) -> float:
        try:
            return float(self.env.elapsed_seconds)
        except Exception:
            return 0.0

    def _gap(self) -> float:
        try:
            return float(self.env.gap_seconds)
        except Exception:
            return 60.0

    def _restart_overhead(self) -> float:
        try:
            return float(self.restart_overhead)
        except Exception:
            return 12 * 60.0  # default 12 minutes

    def _deadline(self) -> float:
        try:
            return float(self.deadline)
        except Exception:
            return 0.0

    def _task_duration(self) -> float:
        try:
            return float(self.task_duration)
        except Exception:
            # fallback to 24 hours
            return 24 * 3600.0

    def _done_so_far(self) -> float:
        try:
            return float(sum(self.task_done_time))
        except Exception:
            return 0.0

    def _remaining_work(self) -> float:
        rem = self._task_duration() - self._done_so_far()
        return max(0.0, rem)

    def _update_observation(self, has_spot: bool, last_cluster_type: ClusterType) -> None:
        # Update statistics for the current region with current availability
        r = self.env.get_current_region()
        now = self._time_now()
        self._last_observed_time[r] = now
        self._seen_count[r] += 1
        if has_spot:
            self._spot_count[r] += 1
        # EMA update
        alpha = 0.05
        self._ema_avail[r] = (1 - alpha) * self._ema_avail[r] + alpha * (1.0 if has_spot else 0.0)
        # Streaks
        if has_spot:
            self._uptime_streak[r] += 1
            self._downtime_streak[r] = 0
        else:
            # If we were on spot last step and it's now unavailable, set cooldown for this region.
            if last_cluster_type == ClusterType.SPOT:
                cooldown_seconds = max(2 * self._restart_overhead(), 5 * self._gap())
                cooldown_seconds = min(cooldown_seconds, 3600.0)  # cap at 1 hour
                self._cooldown_until[r] = max(self._cooldown_until[r], now + cooldown_seconds)
            self._uptime_streak[r] = 0
            self._downtime_streak[r] += 1

    def _should_lock_on_demand(self) -> bool:
        # Decide whether to commit to On-Demand to ensure deadline
        now = self._time_now()
        rem_work = self._remaining_work()
        if rem_work <= 0:
            return False
        # If we switch to OD now, overhead is incurred unless already on OD
        try:
            already_on_od = (self.env.cluster_type == ClusterType.ON_DEMAND)
        except Exception:
            already_on_od = False
        additional_overhead = 0.0 if already_on_od else self._restart_overhead()
        # Fudge to account for step granularity and other minor delays
        fudge = max(2 * self._gap(), 0.05 * rem_work)
        latest_start = self._deadline() - (rem_work + additional_overhead)
        # Lock if at or after latest start (minus fudge)
        return now >= (latest_start - fudge)

    def _region_score(self, idx: int, now: float) -> float:
        # Higher score => better candidate to probe when current region has no spot.
        ema = self._ema_avail[idx]
        uptime = self._uptime_streak[idx]
        downtime = self._downtime_streak[idx]
        in_cooldown = now < self._cooldown_until[idx]
        score = ema
        # reward longer uptimes slightly
        score += 0.01 * min(uptime, 200)
        # penalize recent downtimes
        score -= 0.005 * min(downtime, 300)
        # cooldown penalty
        if in_cooldown:
            # The closer to cooldown end, smaller penalty; but keep a strong penalty
            remaining = self._cooldown_until[idx] - now
            score -= 0.3 + min(0.2, remaining / max(self._gap(), 1.0) * 0.02)
        return score

    def _pick_next_region_to_probe(self) -> int:
        # Choose the region with best score to look for spot
        n = self._num_regions
        now = self._time_now()
        scores = [(self._region_score(i, now), i) for i in range(n)]
        # Shuffle for random tie-breaking
        self._rng.shuffle(scores)
        scores.sort(reverse=True)
        best_idx = scores[0][1]
        current = self.env.get_current_region()
        if best_idx == current and n > 1:
            # If current is already best but has no spot, pick the next best
            for _, idx in scores:
                if idx != current:
                    best_idx = idx
                    break
        return best_idx

    # ------------- Decision logic -------------
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_initialized()

        # Update per-region statistics with current observation
        self._update_observation(has_spot, last_cluster_type)

        # If we've already committed to On-Demand, stay on it
        if self._od_locked:
            return ClusterType.ON_DEMAND

        # If we must commit to OD to meet deadline
        if self._should_lock_on_demand():
            self._od_locked = True
            return ClusterType.ON_DEMAND

        # Prefer Spot when available
        if has_spot:
            return ClusterType.SPOT

        # No spot in current region: Decide whether to wait/scan or switch to OD anyway
        # Check how much slack we have compared to remaining work
        now = self._time_now()
        rem_work = self._remaining_work()
        remaining_time = self._deadline() - now

        # If remaining time is tight relative to remaining work, go OD immediately to be safe
        # Consider overhead if we go OD now
        additional_overhead = self._restart_overhead()
        # Add a small buffer
        tight_buffer = max(3 * self._gap(), 0.02 * self._task_duration())
        if remaining_time <= rem_work + additional_overhead + tight_buffer:
            self._od_locked = True
            return ClusterType.ON_DEMAND

        # Otherwise, scan other regions for spot availability by switching regions and idling this step (NONE)
        target_region = self._pick_next_region_to_probe()
        if target_region != self.env.get_current_region():
            self.env.switch_region(target_region)

        # Idle this step to probe the new region's availability next step
        return ClusterType.NONE