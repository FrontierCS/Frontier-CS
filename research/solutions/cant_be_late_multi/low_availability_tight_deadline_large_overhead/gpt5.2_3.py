import json
import math
from argparse import Namespace
from typing import Any, Callable, List, Optional, Sequence, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_adaptive_v1"

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

        self._init_done = False
        self._done_sum = 0.0
        self._done_idx = 0

        self._n_regions = 1
        self._avail_cnt = [0]
        self._total_cnt = [0]

        self._commit_od = False
        self._od_hold_steps = 0
        self._min_od_hold_steps = 1
        self._commit_buffer = 0.0
        self._idle_budget = 0.0
        self._idle_max_step_fraction = 0.0

        self._gap = 0.0
        self._restart_overhead_s = 0.0
        self._deadline_s = 0.0
        self._task_duration_s = 0.0

        self._ct_spot = ClusterType.SPOT
        self._ct_od = ClusterType.ON_DEMAND
        self._ct_none = getattr(ClusterType, "NONE", None)
        if self._ct_none is None:
            self._ct_none = getattr(ClusterType, "None", None)

        self._env_has_spot_attr = None
        self._env_has_spot_methods: List[str] = [
            "get_has_spot",
            "has_spot_in_region",
            "get_spot_available",
            "get_spot_availability",
            "get_region_spot",
            "get_region_has_spot",
            "spot_available_in_region",
        ]
        self._env_spot_vector_attrs: List[str] = [
            "spot_availability",
            "spot_available",
            "has_spot_by_region",
            "region_spot_availability",
            "spot_availabilities",
        ]
        return self

    def _lazy_init(self) -> None:
        if self._init_done:
            return
        self._init_done = True

        env = getattr(self, "env", None)
        if env is not None and hasattr(env, "get_num_regions") and callable(env.get_num_regions):
            try:
                self._n_regions = int(env.get_num_regions())
            except Exception:
                self._n_regions = 1
        else:
            self._n_regions = 1

        self._avail_cnt = [0] * self._n_regions
        self._total_cnt = [0] * self._n_regions

        self._gap = float(getattr(env, "gap_seconds", 3600.0)) if env is not None else 3600.0

        self._deadline_s = self._as_scalar_seconds(getattr(self, "deadline", 0.0))
        self._task_duration_s = self._as_scalar_seconds(getattr(self, "task_duration", 0.0))
        self._restart_overhead_s = self._as_scalar_seconds(getattr(self, "restart_overhead", 0.0))

        overhead_steps = 0
        if self._gap > 0:
            overhead_steps = int(math.ceil(self._restart_overhead_s / self._gap))
        self._min_od_hold_steps = max(1, overhead_steps + 1)

        # Commit to on-demand when slack is too small to safely absorb a few more restarts.
        self._commit_buffer = (2.0 * self._restart_overhead_s) + float(overhead_steps + 2) * self._gap

        # Idle budget to avoid on-demand briefly during outages; keep conservative.
        initial_slack = max(0.0, self._deadline_s - self._task_duration_s)
        self._idle_budget = min(6.0 * 3600.0, 0.33 * initial_slack)
        self._idle_max_step_fraction = 0.5  # only idle when slack is comfortably large

        # Determine if env has a direct "current has_spot" attribute.
        if env is not None:
            for a in ("has_spot", "current_has_spot", "spot_is_available", "spot_available_now"):
                if hasattr(env, a):
                    self._env_has_spot_attr = a
                    break

    @staticmethod
    def _as_scalar_seconds(x: Any) -> float:
        if isinstance(x, (list, tuple)):
            if not x:
                return 0.0
            return float(x[0])
        return float(x)

    def _update_done_sum(self) -> None:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return

        # Support either flat list or list-of-lists (multi-task).
        if isinstance(tdt, (list, tuple)) and tdt and isinstance(tdt[0], (list, tuple)):
            tdt0 = tdt[0]
        else:
            tdt0 = tdt

        if not isinstance(tdt0, (list, tuple)):
            return

        n = len(tdt0)
        if n <= self._done_idx:
            return
        self._done_sum += float(sum(tdt0[self._done_idx : n]))
        self._done_idx = n

    def _posterior_mean(self, i: int) -> float:
        # Beta(1,1) prior
        a = self._avail_cnt[i] + 1
        b = (self._total_cnt[i] - self._avail_cnt[i]) + 1
        return a / (a + b)

    def _best_region(self, exclude: Optional[int] = None) -> int:
        best_i = 0
        best_s = -1.0
        for i in range(self._n_regions):
            if exclude is not None and i == exclude:
                continue
            s = self._posterior_mean(i)
            if s > best_s + 1e-15 or (abs(s - best_s) <= 1e-15 and i < best_i):
                best_s = s
                best_i = i
        return best_i

    def _env_get_has_spot_region(self, region_idx: int) -> Optional[bool]:
        env = self.env

        for attr in self._env_spot_vector_attrs:
            v = getattr(env, attr, None)
            if v is None:
                continue
            try:
                if isinstance(v, (list, tuple)) and len(v) > region_idx:
                    vv = v[region_idx]
                    if vv is True or vv is False:
                        return bool(vv)
                # numpy arrays or similar
                if hasattr(v, "__len__") and len(v) > region_idx:
                    vv = v[region_idx]
                    if vv is True or vv is False:
                        return bool(vv)
            except Exception:
                pass

        for name in self._env_has_spot_methods:
            fn = getattr(env, name, None)
            if not callable(fn):
                continue
            try:
                r = fn(region_idx)
                if r is True or r is False:
                    return bool(r)
            except TypeError:
                try:
                    r = fn(region_idx=region_idx)
                    if r is True or r is False:
                        return bool(r)
                except Exception:
                    pass
            except Exception:
                pass

        if self._env_has_spot_attr is not None and hasattr(env, "switch_region") and callable(env.switch_region):
            # Best-effort: switch temporarily and read current-spot attribute.
            cur = None
            try:
                cur = env.get_current_region()
            except Exception:
                cur = None
            try:
                env.switch_region(region_idx)
                vv = getattr(env, self._env_has_spot_attr, None)
                if vv is True or vv is False:
                    return bool(vv)
            except Exception:
                return None
            finally:
                try:
                    if cur is not None:
                        env.switch_region(cur)
                except Exception:
                    pass

        return None

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._update_done_sum()

        env = self.env
        try:
            cur_region = int(env.get_current_region())
        except Exception:
            cur_region = 0

        if 0 <= cur_region < self._n_regions:
            self._total_cnt[cur_region] += 1
            if has_spot:
                self._avail_cnt[cur_region] += 1

        remaining_work = max(0.0, self._task_duration_s - self._done_sum)
        if remaining_work <= 0.0:
            return self._ct_none if self._ct_none is not None else self._ct_od

        elapsed = float(getattr(env, "elapsed_seconds", 0.0))
        time_left = max(0.0, self._deadline_s - elapsed)

        overhead_rem = getattr(self, "remaining_restart_overhead", 0.0)
        try:
            overhead_rem = float(overhead_rem)
        except Exception:
            overhead_rem = 0.0
        overhead_rem = max(0.0, overhead_rem)

        slack = time_left - (remaining_work + overhead_rem)
        if slack <= self._commit_buffer:
            self._commit_od = True

        if self._commit_od:
            # Avoid extra restarts near the deadline.
            return self._ct_od

        # If a restart overhead is still pending, avoid changes that reset it, unless forced.
        if overhead_rem > 1e-9:
            if last_cluster_type == self._ct_spot:
                if has_spot:
                    return self._ct_spot
                self._od_hold_steps = max(self._od_hold_steps, self._min_od_hold_steps)
                # We can reposition while switching away from spot.
                best = self._best_region()
                if best != cur_region:
                    try:
                        env.switch_region(best)
                        cur_region = best
                    except Exception:
                        pass
                return self._ct_od
            if last_cluster_type == self._ct_od:
                if self._od_hold_steps > 0:
                    self._od_hold_steps -= 1
                return self._ct_od
            # If we were idle, prefer progress.
            return self._ct_od if not has_spot else self._ct_spot

        # Hysteresis while on on-demand to reduce flapping and overhead.
        if last_cluster_type == self._ct_od:
            if self._od_hold_steps > 0:
                self._od_hold_steps -= 1
                return self._ct_od
            if has_spot and slack > (1.5 * self._commit_buffer):
                return self._ct_spot
            return self._ct_od

        if last_cluster_type == self._ct_spot:
            if has_spot:
                return self._ct_spot

            # No spot in current region. Either idle briefly (if plenty of slack), or use on-demand.
            if self._idle_budget > 0.0 and slack > (self._idle_max_step_fraction * max(1.0, time_left)):
                self._idle_budget = max(0.0, self._idle_budget - self._gap)
                # While idling, optionally reposition to best region for next step (safe: still not returning SPOT).
                best = self._best_region()
                if best != cur_region:
                    try:
                        env.switch_region(best)
                    except Exception:
                        pass
                return self._ct_none if self._ct_none is not None else self._ct_od

            self._od_hold_steps = max(self._od_hold_steps, self._min_od_hold_steps)
            best = self._best_region()
            if best != cur_region:
                try:
                    env.switch_region(best)
                except Exception:
                    pass
            return self._ct_od

        # If last was NONE or unknown:
        if has_spot and slack > (1.5 * self._commit_buffer):
            return self._ct_spot

        # Reposition to best region while using on-demand.
        best = self._best_region()
        if best != cur_region:
            try:
                env.switch_region(best)
            except Exception:
                pass
        self._od_hold_steps = max(self._od_hold_steps, self._min_od_hold_steps)
        return self._ct_od