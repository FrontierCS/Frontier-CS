import json
import math
import os
import gzip
from argparse import Namespace
from typing import List, Optional, Tuple, Any

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _open_maybe_gzip(path: str, mode: str = "rt"):
    if path.endswith(".gz"):
        return gzip.open(path, mode)
    return open(path, mode)


def _parse_bool_token(tok: str) -> Optional[bool]:
    t = tok.strip().lower()
    if t in ("1", "true", "t", "yes", "y"):
        return True
    if t in ("0", "false", "f", "no", "n"):
        return False
    return None


def _load_trace_file(path: str) -> List[bool]:
    # Robust loader: supports json, simple txt/csv, jsonl, gzip.
    try:
        with _open_maybe_gzip(path, "rb") as f:
            head = f.read(64)
        if head.startswith(b"\x93NUMPY"):
            try:
                import numpy as np  # type: ignore
                arr = np.load(path, allow_pickle=True)
                flat = arr.reshape(-1).tolist()
                out = []
                for x in flat:
                    if isinstance(x, (bool, int, float)):
                        out.append(bool(float(x) > 0.5))
                    elif isinstance(x, str):
                        b = _parse_bool_token(x)
                        if b is None:
                            try:
                                out.append(bool(float(x) > 0.5))
                            except Exception:
                                out.append(False)
                        else:
                            out.append(b)
                    else:
                        out.append(False)
                return out
            except Exception:
                pass
        if head.lstrip().startswith(b"{") or head.lstrip().startswith(b"["):
            with _open_maybe_gzip(path, "rt") as f:
                data = json.load(f)
            if isinstance(data, list):
                return [bool(float(x) > 0.5) if not isinstance(x, bool) else x for x in data]
            if isinstance(data, dict):
                candidate = None
                for v in data.values():
                    if isinstance(v, list) and (candidate is None or len(v) > len(candidate)):
                        candidate = v
                if candidate is None:
                    return []
                return [bool(float(x) > 0.5) if not isinstance(x, bool) else x for x in candidate]
    except Exception:
        pass

    out: List[bool] = []
    try:
        with _open_maybe_gzip(path, "rt") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                parts = s.replace(",", " ").split()
                if not parts:
                    continue
                tok = parts[-1]
                b = _parse_bool_token(tok)
                if b is not None:
                    out.append(b)
                else:
                    try:
                        out.append(float(tok) > 0.5)
                    except Exception:
                        out.append(False)
    except Exception:
        return []
    return out


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_v1"

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

        self._trace_files: List[str] = list(config.get("trace_files", []))
        self._spot_traces_raw: List[List[bool]] = []
        for p in self._trace_files:
            try:
                self._spot_traces_raw.append(_load_trace_file(p))
            except Exception:
                self._spot_traces_raw.append([])

        self._precomputed = False
        self._T = 0
        self._R = 0
        self._gap = 0.0
        self._restart_overhead = 0.0
        self._deadline = 0.0
        self._task_duration = 0.0

        self._avail: List[List[bool]] = []
        self._run_len: List[List[int]] = []
        self._best_region: List[int] = []
        self._best_run: List[int] = []
        self._any_spot: List[bool] = []
        self._next_any_spot: List[int] = []

        self._od_committed = False
        self._done_work = 0.0
        self._tdt_len = 0
        return self

    def _ensure_precomputed(self) -> None:
        if self._precomputed:
            return

        def _as_float_seconds(x: Any) -> float:
            if isinstance(x, (list, tuple)) and x:
                x = x[0]
            try:
                return float(x)
            except Exception:
                return 0.0

        self._gap = float(getattr(self.env, "gap_seconds", 60.0))
        self._restart_overhead = _as_float_seconds(getattr(self, "restart_overhead", 0.0))
        self._deadline = _as_float_seconds(getattr(self, "deadline", 0.0))
        self._task_duration = _as_float_seconds(getattr(self, "task_duration", 0.0))

        try:
            self._R = int(self.env.get_num_regions())
        except Exception:
            self._R = max(1, len(self._spot_traces_raw))

        if self._gap <= 0:
            self._gap = 60.0

        self._T = int(math.ceil(self._deadline / self._gap)) if self._deadline > 0 else 0
        if self._T <= 0:
            self._T = 1

        self._avail = [[False] * self._T for _ in range(self._R)]
        for r in range(self._R):
            src = self._spot_traces_raw[r] if r < len(self._spot_traces_raw) else []
            if not src:
                continue
            n = min(len(src), self._T)
            row = self._avail[r]
            for i in range(n):
                row[i] = bool(src[i])
            # remainder stays False

        self._run_len = [[0] * (self._T + 1) for _ in range(self._R)]
        for r in range(self._R):
            rl = self._run_len[r]
            av = self._avail[r]
            for t in range(self._T - 1, -1, -1):
                rl[t] = (rl[t + 1] + 1) if av[t] else 0

        self._best_region = [-1] * self._T
        self._best_run = [0] * self._T
        self._any_spot = [False] * self._T
        for t in range(self._T):
            best_r = -1
            best_len = 0
            any_s = False
            for r in range(self._R):
                l = self._run_len[r][t]
                if l > 0:
                    any_s = True
                    if l > best_len:
                        best_len = l
                        best_r = r
            self._best_region[t] = best_r
            self._best_run[t] = best_len
            self._any_spot[t] = any_s

        self._next_any_spot = [self._T] * (self._T + 1)
        nxt = self._T
        for t in range(self._T - 1, -1, -1):
            if self._any_spot[t]:
                nxt = t
            self._next_any_spot[t] = nxt
        self._next_any_spot[self._T] = self._T

        self._precomputed = True

    def _update_done_work(self) -> None:
        tdt = getattr(self, "task_done_time", None)
        if not isinstance(tdt, list):
            self._done_work = 0.0
            self._tdt_len = 0
            return
        n = len(tdt)
        if n > self._tdt_len:
            try:
                self._done_work += float(sum(tdt[self._tdt_len:]))
            except Exception:
                pass
            self._tdt_len = n

    def _predict_step_work(self, last_cluster_type: ClusterType, cur_region: int, action_type: ClusterType, action_region: int) -> float:
        if action_type == ClusterType.NONE:
            return 0.0
        restart = False
        if last_cluster_type == ClusterType.NONE:
            restart = True
        elif action_type != last_cluster_type:
            restart = True
        elif action_region != cur_region:
            restart = True
        oh_start = self._restart_overhead if restart else float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        paid = self._gap if oh_start >= self._gap else oh_start
        work = self._gap - paid
        if work < 0:
            work = 0.0
        return work

    def _can_finish_if_start_on_demand_next(self, remaining_work_after: float, time_left_after: float) -> bool:
        # Conservative: assume a full restart overhead is needed when (re)starting on-demand.
        return remaining_work_after <= (time_left_after - self._restart_overhead + 1e-9)

    def _pick_spot_region_now(self, t: int, cur_region: int, has_spot_now: bool) -> int:
        # Choose a region with spot at current step; prefer current region to reduce switching unless
        # another region has much longer run.
        if t < 0 or t >= self._T or self._R <= 0:
            return cur_region

        # Availability in current region according to env signal should take priority.
        cur_has = has_spot_now
        cur_run = self._run_len[cur_region][t] if 0 <= cur_region < self._R else 0
        if cur_has and cur_run <= 0:
            cur_run = 1

        best_r = self._best_region[t]
        best_run = self._best_run[t]

        if best_r < 0:
            return cur_region

        if cur_has:
            # If switching likely doesn't pay off, stay.
            # Switching effectively costs ~restart_overhead productive time.
            benefit = (best_run - cur_run) * self._gap
            if benefit <= self._restart_overhead + 1e-9:
                return cur_region
        return best_r

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_precomputed()
        self._update_done_work()

        if self._done_work >= self._task_duration - 1e-9:
            return ClusterType.NONE

        cur_region = 0
        try:
            cur_region = int(self.env.get_current_region())
        except Exception:
            cur_region = 0

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        t = int(elapsed // self._gap) if self._gap > 0 else 0
        if t < 0:
            t = 0

        remaining_work = self._task_duration - self._done_work
        if remaining_work < 0:
            remaining_work = 0.0
        time_left = self._deadline - elapsed
        if time_left < 0:
            time_left = 0.0

        # If we've committed to on-demand, never switch back.
        if self._od_committed:
            return ClusterType.ON_DEMAND

        # If already on-demand, keep it (avoids wasted restarts).
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._od_committed = True
            return ClusterType.ON_DEMAND

        # Safety: if we cannot afford any further delay (even one step with 0 work), start on-demand.
        if remaining_work >= time_left - self._restart_overhead - 1e-9:
            self._od_committed = True
            return ClusterType.ON_DEMAND

        # Helper to finalize a non-spot action and optionally reposition while idle.
        def choose_none_and_reposition() -> ClusterType:
            # If returning NONE, set up next region for spot if possible.
            t_next = t + 1
            if t_next < self._T:
                r_next = self._best_region[t_next]
                if r_next is not None and isinstance(r_next, int) and r_next >= 0 and r_next != cur_region:
                    try:
                        self.env.switch_region(int(r_next))
                    except Exception:
                        pass
            return ClusterType.NONE

        # If spot not available in current region, we must not return SPOT (per spec).
        if not has_spot:
            # Decide NONE vs ON_DEMAND conservatively.
            # If after idling one step, on-demand can still finish, idle and reposition; else on-demand now.
            time_left_after = time_left - self._gap
            if time_left_after < 0:
                time_left_after = 0.0
            if self._can_finish_if_start_on_demand_next(remaining_work, time_left_after):
                return choose_none_and_reposition()
            self._od_committed = True
            return ClusterType.ON_DEMAND

        # has_spot is True in current region: decide SPOT vs NONE vs ON_DEMAND.
        oh = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)

        # If we're already running spot, decide if continuing can yield any work before spot ends.
        if last_cluster_type == ClusterType.SPOT:
            run_remaining = 1
            if 0 <= cur_region < self._R and 0 <= t < self._T:
                run_remaining = self._run_len[cur_region][t]
                if run_remaining <= 0:
                    run_remaining = 1

            # If the remaining spot window is too short to finish the pending overhead, avoid paying for no progress.
            if oh > 1e-9 and run_remaining * self._gap <= oh + 1e-9:
                # Can we afford to idle this step and still finish on-demand after?
                time_left_after = time_left - self._gap
                if time_left_after < 0:
                    time_left_after = 0.0
                if self._can_finish_if_start_on_demand_next(remaining_work, time_left_after):
                    return choose_none_and_reposition()
                self._od_committed = True
                return ClusterType.ON_DEMAND

            # Safety check after taking SPOT this step (work may be reduced by overhead).
            work_this = self._predict_step_work(last_cluster_type, cur_region, ClusterType.SPOT, cur_region)
            remaining_after = remaining_work - work_this
            time_left_after = time_left - self._gap
            if time_left_after < 0:
                time_left_after = 0.0
            if remaining_after < 0:
                remaining_after = 0.0
            if not self._can_finish_if_start_on_demand_next(remaining_after, time_left_after):
                self._od_committed = True
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # Not currently on spot: decide whether to start spot now, and which region.
        if t >= self._T:
            self._od_committed = True
            return ClusterType.ON_DEMAND

        target_region = self._pick_spot_region_now(t, cur_region, has_spot)
        if target_region != cur_region:
            # Only switch if our precomputed trace indicates spot exists now in target.
            ok_to_switch = True
            if 0 <= target_region < self._R and 0 <= t < self._T:
                ok_to_switch = bool(self._avail[target_region][t])
            if ok_to_switch:
                try:
                    self.env.switch_region(int(target_region))
                    cur_region = target_region
                except Exception:
                    pass

        # Determine if starting spot now can produce any work within the current consecutive window.
        run_now = 1
        if 0 <= cur_region < self._R and 0 <= t < self._T:
            run_now = self._run_len[cur_region][t]
            if run_now <= 0:
                run_now = 1

        # Starting spot from non-spot incurs full restart overhead.
        if run_now * self._gap <= self._restart_overhead + 1e-9:
            # Not worth starting spot; choose NONE if safe else on-demand.
            time_left_after = time_left - self._gap
            if time_left_after < 0:
                time_left_after = 0.0
            if self._can_finish_if_start_on_demand_next(remaining_work, time_left_after):
                return choose_none_and_reposition()
            self._od_committed = True
            return ClusterType.ON_DEMAND

        # Safety check after taking SPOT this step.
        work_this = self._predict_step_work(last_cluster_type, cur_region, ClusterType.SPOT, cur_region)
        remaining_after = remaining_work - work_this
        time_left_after = time_left - self._gap
        if time_left_after < 0:
            time_left_after = 0.0
        if remaining_after < 0:
            remaining_after = 0.0
        if not self._can_finish_if_start_on_demand_next(remaining_after, time_left_after):
            self._od_committed = True
            return ClusterType.ON_DEMAND

        return ClusterType.SPOT
