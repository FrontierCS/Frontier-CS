import json
from argparse import Namespace
from typing import Any, Callable, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cbl_multi_region_adaptive_v1"

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

        self._runtime_inited = False

        self._tdt_len = 0
        self._work_done = 0.0

        self._spot_query: Optional[Callable[[int], bool]] = None
        self._spot_query_detected = False
        self._step_idx_func: Optional[Callable[[], int]] = None

        self._locked_ondemand = False
        self._cooldown_steps = 0

        self._prev_remaining_overhead: Optional[float] = None
        self._prev_choice: Optional[ClusterType] = None

        return self

    def _init_runtime(self) -> None:
        if self._runtime_inited:
            return
        self._runtime_inited = True

        self._CT_SPOT = ClusterType.SPOT
        self._CT_OD = ClusterType.ON_DEMAND
        self._CT_NONE = getattr(ClusterType, "NONE", None)
        if self._CT_NONE is None:
            self._CT_NONE = getattr(ClusterType, "None", None)

        env = self.env
        self._gap = float(getattr(env, "gap_seconds", 1.0))
        self._restart_overhead = float(getattr(self, "restart_overhead", 0.0))

        self._min_switch_slack = max(2.0 * self._gap, 2.0 * self._restart_overhead)

        self._panic_buffer = max(2.0 * self._gap, 4.0 * self._restart_overhead, 15.0 * 60.0)
        self._wait_slack = max(2.0 * 3600.0, 10.0 * self._gap)
        self._lock_slack = max(self._panic_buffer, 30.0 * 60.0)

        self._cooldown_default = max(1, int(self._restart_overhead / max(self._gap, 1e-9)) + 1)

    def _update_work_done(self) -> None:
        tdt = self.task_done_time
        ln = len(tdt)
        prev = self._tdt_len
        if ln <= prev:
            return
        wd = self._work_done
        for i in range(prev, ln):
            wd += float(tdt[i])
        self._work_done = wd
        self._tdt_len = ln

    def _compute_step_idx(self) -> int:
        if self._step_idx_func is not None:
            return self._step_idx_func()
        env = self.env
        for name in ("timestep", "time_idx", "step", "current_step", "_timestep", "_step"):
            if hasattr(env, name):
                v = getattr(env, name)
                try:
                    if callable(v):
                        vv = int(v())
                    else:
                        vv = int(v)
                    def _f(vv_attr=name):
                        vv2 = getattr(self.env, vv_attr)
                        return int(vv2() if callable(vv2) else vv2)
                    self._step_idx_func = _f
                    return vv
                except Exception:
                    pass
        def _f():
            g = float(getattr(self.env, "gap_seconds", 1.0))
            e = float(getattr(self.env, "elapsed_seconds", 0.0))
            if g <= 0:
                return 0
            return int(e // g)
        self._step_idx_func = _f
        return _f()

    def _detect_spot_query(self, has_spot_current: bool) -> None:
        if self._spot_query_detected:
            return
        self._spot_query_detected = True

        env = self.env
        try:
            n = int(env.get_num_regions())
            cur = int(env.get_current_region())
        except Exception:
            return

        step_idx = self._compute_step_idx()

        method_names = (
            "get_has_spot",
            "has_spot_in_region",
            "get_spot_availability",
            "get_spot_available",
            "spot_available_in_region",
            "is_spot_available",
            "spot_available",
        )
        for name in method_names:
            fn = getattr(env, name, None)
            if not callable(fn):
                continue
            try:
                v = fn(cur)
                if bool(v) != bool(has_spot_current):
                    continue
                _ = fn(0 if n > 0 else cur)
                self._spot_query = lambda i, _fn=fn: bool(_fn(int(i)))
                return
            except TypeError:
                continue
            except Exception:
                continue

        candidate_names = []
        for obj_name in dir(env):
            low = obj_name.lower()
            if ("spot" in low and ("trace" in low or "avail" in low)) or (low.startswith("trace") and "spot" in low):
                candidate_names.append(obj_name)
        candidate_names.extend(["spot_traces", "spot_trace", "spot_availability", "_spot_traces", "_spot_availability", "traces"])

        seen = set()
        for name in candidate_names:
            if name in seen:
                continue
            seen.add(name)
            try:
                obj = getattr(env, name)
            except Exception:
                continue
            if not isinstance(obj, (list, tuple)):
                continue
            if len(obj) != n:
                continue
            try:
                reg0 = obj[cur]
            except Exception:
                continue
            if not isinstance(reg0, (list, tuple)):
                continue
            if step_idx < 0 or step_idx >= len(reg0):
                continue
            try:
                vcur = reg0[step_idx]
            except Exception:
                continue
            try:
                if bool(vcur) != bool(has_spot_current):
                    continue
            except Exception:
                continue

            def _mk_query(_obj: Any):
                def _q(i: int) -> bool:
                    ii = int(i)
                    rr = _obj[ii]
                    si = self._compute_step_idx()
                    if si < 0:
                        si = 0
                    if si >= len(rr):
                        si = len(rr) - 1
                    return bool(rr[si])
                return _q

            self._spot_query = _mk_query(obj)
            return

    def _best_spot_region(self) -> Optional[int]:
        if self._spot_query is None:
            return None
        env = self.env
        try:
            n = int(env.get_num_regions())
            cur = int(env.get_current_region())
        except Exception:
            return None

        try:
            if self._spot_query(cur):
                return cur
        except Exception:
            pass

        for i in range(n):
            if i == cur:
                continue
            try:
                if self._spot_query(i):
                    return i
            except Exception:
                continue
        return None

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_runtime()
        self._update_work_done()
        self._detect_spot_query(has_spot)

        env = self.env
        now = float(getattr(env, "elapsed_seconds", 0.0))

        work_left = float(self.task_duration) - float(self._work_done)
        if work_left <= 0.0:
            self._prev_remaining_overhead = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
            self._prev_choice = self._CT_NONE
            return self._CT_NONE

        time_left = float(self.deadline) - now
        if time_left <= 0.0:
            self._prev_remaining_overhead = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
            self._prev_choice = self._CT_NONE
            return self._CT_NONE

        overhead_pending = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        slack = time_left - overhead_pending - work_left

        if slack <= self._lock_slack:
            self._locked_ondemand = True

        if self._cooldown_steps > 0:
            self._cooldown_steps -= 1

        if slack <= self._panic_buffer:
            choice = self._CT_OD
            self._locked_ondemand = True
            self._prev_remaining_overhead = overhead_pending
            self._prev_choice = choice
            return choice

        if overhead_pending > 1e-9 and overhead_pending < 0.5 * self._restart_overhead:
            if last_cluster_type == self._CT_OD:
                choice = self._CT_OD
                self._prev_remaining_overhead = overhead_pending
                self._prev_choice = choice
                return choice
            if last_cluster_type == self._CT_SPOT and has_spot and not self._locked_ondemand:
                choice = self._CT_SPOT
                self._prev_remaining_overhead = overhead_pending
                self._prev_choice = choice
                return choice
            if slack >= self._wait_slack and not self._locked_ondemand:
                choice = self._CT_NONE
                self._prev_remaining_overhead = overhead_pending
                self._prev_choice = choice
                return choice
            choice = self._CT_OD
            self._locked_ondemand = True
            self._prev_remaining_overhead = overhead_pending
            self._prev_choice = choice
            return choice

        if self._locked_ondemand:
            choice = self._CT_OD
            self._prev_remaining_overhead = overhead_pending
            self._prev_choice = choice
            return choice

        if has_spot:
            choice = self._CT_SPOT
            self._prev_remaining_overhead = overhead_pending
            self._prev_choice = choice
            return choice

        if self._spot_query is not None and slack > self._min_switch_slack and self._cooldown_steps == 0:
            target = self._best_spot_region()
            if target is not None:
                try:
                    cur_region = int(env.get_current_region())
                except Exception:
                    cur_region = None
                if cur_region is None or target != cur_region:
                    try:
                        env.switch_region(int(target))
                        self._cooldown_steps = self._cooldown_default
                    except Exception:
                        target = None
                if target is not None:
                    choice = self._CT_SPOT
                    self._prev_remaining_overhead = overhead_pending
                    self._prev_choice = choice
                    return choice

        if slack >= self._wait_slack:
            choice = self._CT_NONE
            self._prev_remaining_overhead = overhead_pending
            self._prev_choice = choice
            return choice

        choice = self._CT_OD
        self._locked_ondemand = True
        self._prev_remaining_overhead = overhead_pending
        self._prev_choice = choice
        return choice
