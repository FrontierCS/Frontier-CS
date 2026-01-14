import json
import math
from argparse import Namespace
from typing import Any, List, Optional, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


_CT_SPOT = getattr(ClusterType, "SPOT", None)
_CT_ONDEMAND = getattr(ClusterType, "ON_DEMAND", None)
_CT_NONE = getattr(ClusterType, "NONE", getattr(ClusterType, "None", None))


def _as_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


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

        self._panic = False

        self._done_seconds = 0.0
        self._last_done_len = 0

        self._traces_loaded = False
        self._trace_avail: List[List[bool]] = []
        self._run_len: List[List[int]] = []
        self._next_one: List[List[int]] = []
        self._union_avail: List[bool] = []
        self._union_suffix: List[int] = []
        self._trace_len = 0
        self._num_trace_regions = 0

        trace_files = config.get("trace_files", [])
        if isinstance(trace_files, list) and trace_files:
            try:
                self._load_and_precompute_traces(trace_files)
            except Exception:
                self._traces_loaded = False

        return self

    def _get_task_duration(self) -> float:
        td = getattr(self, "task_duration", 0.0)
        if isinstance(td, (list, tuple)):
            return _as_float(td[0], 0.0) if td else 0.0
        return _as_float(td, 0.0)

    def _get_deadline(self) -> float:
        dl = getattr(self, "deadline", 0.0)
        if isinstance(dl, (list, tuple)):
            return _as_float(dl[0], 0.0) if dl else 0.0
        return _as_float(dl, 0.0)

    def _get_restart_overhead(self) -> float:
        oh = getattr(self, "restart_overhead", 0.0)
        if isinstance(oh, (list, tuple)):
            return _as_float(oh[0], 0.0) if oh else 0.0
        return _as_float(oh, 0.0)

    def _load_trace_file(self, path: str) -> List[bool]:
        try:
            with open(path, "r") as f:
                txt = f.read()
        except Exception:
            return []

        s = txt.strip()
        if not s:
            return []

        obj = None
        try:
            obj = json.loads(s)
        except Exception:
            obj = None

        def to_bool(v: Any) -> Optional[bool]:
            if isinstance(v, bool):
                return v
            if isinstance(v, (int, float)):
                return float(v) > 0.0
            if isinstance(v, str):
                t = v.strip().lower()
                if t in ("true", "t", "1", "yes", "y"):
                    return True
                if t in ("false", "f", "0", "no", "n"):
                    return False
                try:
                    return float(t) > 0.0
                except Exception:
                    return None
            return None

        if isinstance(obj, dict):
            for k in ("availability", "avail", "spot", "trace", "data", "values"):
                v = obj.get(k, None)
                if isinstance(v, list):
                    obj = v
                    break

        if isinstance(obj, list):
            if obj and isinstance(obj[0], dict):
                out: List[bool] = []
                for it in obj:
                    if not isinstance(it, dict):
                        continue
                    v = None
                    for k in ("available", "has_spot", "spot", "avail", "value", "is_available"):
                        if k in it:
                            v = it[k]
                            break
                    if v is None:
                        for vv in it.values():
                            if isinstance(vv, (bool, int, float, str)):
                                v = vv
                                break
                    b = to_bool(v)
                    if b is None:
                        continue
                    out.append(b)
                return out
            else:
                out2: List[bool] = []
                for x in obj:
                    b = to_bool(x)
                    if b is None:
                        continue
                    out2.append(b)
                return out2

        # Fallback: parse lines, take last numeric/bool token
        out3: List[bool] = []
        for line in s.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                continue
            parts = [p for p in line.replace(",", " ").split() if p]
            if not parts:
                continue
            token = parts[-1]
            b = to_bool(token)
            if b is None:
                # Try any token in reverse
                for token in reversed(parts):
                    b = to_bool(token)
                    if b is not None:
                        break
            if b is None:
                continue
            out3.append(b)
        return out3

    def _load_and_precompute_traces(self, trace_files: List[str]) -> None:
        traces: List[List[bool]] = []
        for p in trace_files:
            arr = self._load_trace_file(p)
            traces.append(arr)

        if not traces:
            self._traces_loaded = False
            return

        max_len = max((len(a) for a in traces), default=0)
        if max_len <= 0:
            self._traces_loaded = False
            return

        # Pad to same length
        for i in range(len(traces)):
            a = traces[i]
            if len(a) < max_len:
                traces[i] = a + [False] * (max_len - len(a))
            elif len(a) > max_len:
                traces[i] = a[:max_len]

        num_regions = len(traces)
        run_len: List[List[int]] = []
        next_one: List[List[int]] = []

        for r in range(num_regions):
            avail = traces[r]
            rl = [0] * (max_len + 1)
            no = [max_len] * (max_len + 1)
            no[max_len] = max_len
            for i in range(max_len - 1, -1, -1):
                if avail[i]:
                    rl[i] = rl[i + 1] + 1
                    no[i] = i
                else:
                    rl[i] = 0
                    no[i] = no[i + 1]
            run_len.append(rl)
            next_one.append(no)

        union_avail = [False] * max_len
        for i in range(max_len):
            u = False
            for r in range(num_regions):
                if traces[r][i]:
                    u = True
                    break
            union_avail[i] = u

        union_suffix = [0] * (max_len + 1)
        for i in range(max_len - 1, -1, -1):
            union_suffix[i] = union_suffix[i + 1] + (1 if union_avail[i] else 0)

        self._trace_avail = traces
        self._run_len = run_len
        self._next_one = next_one
        self._union_avail = union_avail
        self._union_suffix = union_suffix
        self._trace_len = max_len
        self._num_trace_regions = num_regions
        self._traces_loaded = True

    def _update_done(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not isinstance(tdt, list):
            return self._done_seconds
        n = len(tdt)
        if n > self._last_done_len:
            for seg in tdt[self._last_done_len :]:
                self._done_seconds += _as_float(seg, 0.0)
            self._last_done_len = n
        return self._done_seconds

    def _idx_now(self) -> int:
        gap = _as_float(getattr(self.env, "gap_seconds", 1.0), 1.0)
        t = _as_float(getattr(self.env, "elapsed_seconds", 0.0), 0.0)
        if gap <= 0:
            return 0
        # Avoid float rounding issues at boundaries
        return int((t + 1e-9) // gap)

    def _select_best_region_for_next_spot(self, start_idx: int, num_regions: int) -> int:
        if not self._traces_loaded or self._trace_len <= 0 or self._num_trace_regions <= 0:
            return self.env.get_current_region()

        L = self._trace_len
        idx = start_idx
        if idx < 0:
            idx = 0
        if idx > L:
            idx = L

        cur = self.env.get_current_region()
        best_r = cur
        best_t = 10**18
        best_run = -1

        max_r = min(num_regions, self._num_trace_regions)
        for r in range(max_r):
            t = self._next_one[r][idx]
            if t < best_t:
                best_t = t
                best_r = r
                best_run = self._run_len[r][t] if t < L else 0
            elif t == best_t:
                run = self._run_len[r][t] if t < L else 0
                if run > best_run:
                    best_run = run
                    best_r = r

        return best_r

    def _spot_time_remaining_upper_bound(self, start_idx: int) -> float:
        if not self._traces_loaded or self._trace_len <= 0:
            return 0.0
        L = self._trace_len
        idx = start_idx
        if idx < 0:
            idx = 0
        if idx > L:
            idx = L
        gap = _as_float(getattr(self.env, "gap_seconds", 1.0), 1.0)
        return float(self._union_suffix[idx]) * gap

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done = self._update_done()
        task_duration = self._get_task_duration()
        remaining_work = task_duration - done
        if remaining_work <= 1e-9:
            return _CT_NONE

        deadline = self._get_deadline()
        elapsed = _as_float(getattr(self.env, "elapsed_seconds", 0.0), 0.0)
        time_left = deadline - elapsed
        gap = _as_float(getattr(self.env, "gap_seconds", 1.0), 1.0)
        restart_overhead = self._get_restart_overhead()
        pending_overhead = _as_float(getattr(self, "remaining_restart_overhead", 0.0), 0.0)

        # Panic: if we start/keep on-demand now and don't restart again, can we still finish?
        if not self._panic:
            if last_cluster_type == _CT_ONDEMAND:
                min_needed = remaining_work + max(0.0, pending_overhead)
            else:
                min_needed = remaining_work + max(0.0, restart_overhead)
            if time_left <= min_needed + max(0.0, gap):
                self._panic = True

        if self._panic:
            return _CT_ONDEMAND

        num_regions = self.env.get_num_regions()
        idx = self._idx_now()

        if has_spot:
            return _CT_SPOT

        # Spot not available in current region this step; pick region for next step.
        # For safety, do NOT return SPOT when has_spot is False.
        next_idx = idx + 1

        if self._traces_loaded and num_regions > 1:
            target = self._select_best_region_for_next_spot(next_idx, num_regions)
            cur = self.env.get_current_region()
            if target != cur:
                # If we're already stable on on-demand, avoid thrashy switches unless it helps materially.
                do_switch = True
                if last_cluster_type == _CT_ONDEMAND and pending_overhead <= 1e-9 and self._traces_loaded:
                    L = self._trace_len
                    if cur < self._num_trace_regions and target < self._num_trace_regions:
                        cur_next = self._next_one[cur][min(next_idx, L)]
                        tar_next = self._next_one[target][min(next_idx, L)]
                        # Require at least 2-step earlier spot to justify restarting on-demand
                        if not (tar_next + 1 < cur_next):
                            do_switch = False
                if do_switch:
                    self.env.switch_region(target)

        # Decide whether to pay for on-demand now or wait.
        # Since we can't run spot this step, check if future (from next step) spot time can finish the work.
        if self._traces_loaded:
            spot_future = self._spot_time_remaining_upper_bound(next_idx)
            if spot_future >= remaining_work - 1e-9:
                return _CT_NONE
            return _CT_ONDEMAND

        # No trace: be conservative but cost-aware.
        # Wait unless we're getting close to the deadline.
        min_needed_if_ond = remaining_work + max(0.0, restart_overhead)
        if time_left <= min_needed_if_ond + max(0.0, gap):
            return _CT_ONDEMAND
        return _CT_NONE