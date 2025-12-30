import json
import math
import inspect
from argparse import Namespace
from typing import Optional, Callable, Tuple, Any

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _get_cluster_type(name_candidates):
    for n in name_candidates:
        if hasattr(ClusterType, n):
            return getattr(ClusterType, n)
    return None


_CT_SPOT = _get_cluster_type(("SPOT", "Spot", "spot"))
_CT_ON_DEMAND = _get_cluster_type(("ON_DEMAND", "ONDEMAND", "OnDemand", "on_demand", "ondemand"))
_CT_NONE = _get_cluster_type(("NONE", "None", "none"))


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multiregion_v1"

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

        self._step_count = 0
        self._last_task_done_len = 0
        self._work_done = 0.0

        self._forced_on_demand = False

        self._num_regions = None
        self._region_obs = None
        self._region_spot = None
        self._total_obs = 0

        self._last_region = None
        self._last_switch_step = -10**9

        self._last_action = None

        self._gap = None
        self._restart = None
        self._force_buffer = None

        self._spot_query = None  # type: Optional[Tuple[Callable[..., Any], int, bool]]

        self.trace_files = list(config.get("trace_files", []))

        return self

    def _ensure_constants(self):
        if self._gap is None:
            try:
                self._gap = float(self.env.gap_seconds)
            except Exception:
                self._gap = 1.0
        if self._restart is None:
            try:
                self._restart = float(self.restart_overhead)
            except Exception:
                self._restart = 0.0
        if self._force_buffer is None:
            # Conservative buffer to reduce risk of deadline miss.
            # Tuned to be small relative to 24h slack, but large enough to absorb a few restarts.
            self._force_buffer = 2.0 * self._restart + 2.0 * self._gap

    def _ensure_regions(self):
        if self._num_regions is not None and self._region_obs is not None:
            return
        n = None
        try:
            n = int(self.env.get_num_regions())
        except Exception:
            n = 1
        if n <= 0:
            n = 1
        self._num_regions = n
        self._region_obs = [0] * n
        self._region_spot = [0] * n
        self._total_obs = 0
        try:
            self._last_region = int(self.env.get_current_region())
        except Exception:
            self._last_region = 0

    def _update_work_done(self):
        td = self.task_done_time
        if not td:
            self._last_task_done_len = 0
            self._work_done = 0.0
            return
        l = len(td)
        if l == self._last_task_done_len:
            return
        if l < self._last_task_done_len:
            # Reset occurred
            self._work_done = float(sum(td))
            self._last_task_done_len = l
            return
        # Incremental add
        s = 0.0
        for i in range(self._last_task_done_len, l):
            s += float(td[i])
        self._work_done += s
        self._last_task_done_len = l

    def _discover_spot_query(self) -> Optional[Tuple[Callable[..., Any], int, bool]]:
        env = self.env
        candidates = (
            "has_spot",
            "get_has_spot",
            "spot_available",
            "is_spot_available",
            "get_spot_available",
            "get_spot_availability",
        )
        for name in candidates:
            fn = getattr(env, name, None)
            if fn is None:
                continue
            if not callable(fn):
                # attribute boolean
                try:
                    val = bool(fn)
                    return (lambda _v=val: _v, 0, True)
                except Exception:
                    continue
            try:
                sig = inspect.signature(fn)
                params = sig.parameters
                arity = 0
                for p in params.values():
                    if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) and p.default is p.empty:
                        arity += 1
                # Try call patterns
                if arity == 0:
                    try:
                        v = fn()
                        if isinstance(v, bool) or isinstance(v, (int, float)):
                            return (fn, 0, True)
                    except Exception:
                        pass
                elif arity == 1:
                    # Might accept region index
                    try:
                        r = int(env.get_current_region())
                    except Exception:
                        r = 0
                    try:
                        v = fn(r)
                        if isinstance(v, bool) or isinstance(v, (int, float)):
                            return (fn, 1, True)
                    except Exception:
                        pass
            except Exception:
                continue
        return None

    def _query_current_has_spot(self) -> Optional[bool]:
        if self._spot_query is None:
            self._spot_query = self._discover_spot_query()
        if self._spot_query is None:
            return None
        fn, arity, _ = self._spot_query
        try:
            if arity == 0:
                return bool(fn())
            if arity == 1:
                try:
                    r = int(self.env.get_current_region())
                except Exception:
                    r = 0
                return bool(fn(r))
        except Exception:
            return None
        return None

    def _ucb_best_region(self, exclude_region: int) -> int:
        n = self._num_regions
        total = self._total_obs + 1
        logt = math.log(total + 1.0)
        best_r = exclude_region
        best_score = -1e18
        for r in range(n):
            if r == exclude_region:
                continue
            obs = self._region_obs[r]
            spot = self._region_spot[r]
            mean = (spot + 1.0) / (obs + 2.0)  # Beta(1,1) prior
            bonus = math.sqrt(2.0 * logt / (obs + 1.0))
            score = mean + 0.35 * bonus
            if score > best_score:
                best_score = score
                best_r = r
        return best_r

    def _should_force_on_demand(self, last_cluster_type: ClusterType, remaining_work: float, remaining_time: float) -> bool:
        # Required wall time if we switch to on-demand and keep it:
        # - remaining_work of progress
        # - plus a restart overhead if not already on-demand (switching/starting)
        startup = 0.0 if last_cluster_type == _CT_ON_DEMAND else self._restart
        required = remaining_work + startup
        return remaining_time <= required + self._force_buffer

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._step_count += 1
        self._ensure_constants()
        self._ensure_regions()

        try:
            cur_region = int(self.env.get_current_region())
        except Exception:
            cur_region = 0

        # Track region switching
        if self._last_region is None:
            self._last_region = cur_region
        elif cur_region != self._last_region:
            self._last_switch_step = self._step_count
            self._last_region = cur_region

        # Update observations for current region
        if 0 <= cur_region < self._num_regions:
            self._region_obs[cur_region] += 1
            if has_spot:
                self._region_spot[cur_region] += 1
            self._total_obs += 1

        self._update_work_done()

        task_duration = float(self.task_duration)
        remaining_work = task_duration - self._work_done
        if remaining_work <= 0.0:
            self._last_action = _CT_NONE
            return _CT_NONE

        elapsed = float(self.env.elapsed_seconds)
        remaining_time = float(self.deadline) - elapsed
        if remaining_time <= 0.0:
            # Too late; still try to run on-demand if possible
            self._forced_on_demand = True
            self._last_action = _CT_ON_DEMAND
            return _CT_ON_DEMAND

        if not self._forced_on_demand and self._should_force_on_demand(last_cluster_type, remaining_work, remaining_time):
            self._forced_on_demand = True

        if self._forced_on_demand:
            self._last_action = _CT_ON_DEMAND
            return _CT_ON_DEMAND

        # Not forced: opportunistically use spot when available
        if has_spot:
            self._last_action = _CT_SPOT
            return _CT_SPOT

        # Spot not available: decide between waiting/searching vs on-demand
        # If we wait one more decision interval, can we still comfortably switch to on-demand and finish?
        wait_safe = remaining_time > (remaining_work + self._restart + self._force_buffer + self._gap)

        if wait_safe:
            # Search other regions while waiting, but avoid excessive switching when overhead almost cleared
            do_switch = self._num_regions > 1
            if do_switch:
                # Avoid switching too frequently when we're not in a "search loop"
                # Allow rapid switching if we are already waiting repeatedly with no spot.
                cooldown = 1 if self._last_action == _CT_NONE else max(1, int(self._restart / max(self._gap, 1e-9)))
                if self._step_count - self._last_switch_step < cooldown:
                    do_switch = False

            if do_switch:
                next_region = self._ucb_best_region(exclude_region=cur_region)
                if next_region != cur_region:
                    try:
                        self.env.switch_region(next_region)
                        # If we can query spot availability reliably, we might run spot immediately.
                        q = self._query_current_has_spot()
                        if q is True:
                            self._last_action = _CT_SPOT
                            return _CT_SPOT
                    except Exception:
                        pass

            self._last_action = _CT_NONE
            return _CT_NONE

        # Not safe to wait: use on-demand to stay on track
        self._last_action = _CT_ON_DEMAND
        return _CT_ON_DEMAND