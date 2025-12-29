import json
import math
import gzip
from argparse import Namespace
from array import array
from typing import Any, List, Optional, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _open_maybe_gzip(path: str, mode: str = "rt"):
    if path.endswith(".gz"):
        return gzip.open(path, mode)
    return open(path, mode)


def _coerce_to_01(x: Any) -> int:
    if isinstance(x, bool):
        return 1 if x else 0
    if x is None:
        return 0
    if isinstance(x, (int, float)):
        return 1 if x > 0 else 0
    if isinstance(x, str):
        s = x.strip().lower()
        if not s:
            return 0
        if s in ("1", "true", "t", "yes", "y", "on"):
            return 1
        if s in ("0", "false", "f", "no", "n", "off"):
            return 0
        try:
            v = float(s)
            return 1 if v > 0 else 0
        except Exception:
            return 0
    return 0


def _load_trace_file(path: str) -> List[int]:
    try:
        with _open_maybe_gzip(path, "rb") as f:
            head = f.read(64)
    except Exception:
        return []

    # NPY
    if head.startswith(b"\x93NUMPY"):
        try:
            import numpy as np  # type: ignore

            with _open_maybe_gzip(path, "rb") as f:
                arr = np.load(f, allow_pickle=True)
            flat = arr.reshape(-1).tolist()
            return [_coerce_to_01(v) for v in flat]
        except Exception:
            pass

    # JSON
    if head.lstrip().startswith(b"{") or head.lstrip().startswith(b"["):
        try:
            with _open_maybe_gzip(path, "rt") as f:
                obj = json.load(f)

            def extract(o: Any) -> Optional[List[Any]]:
                if isinstance(o, list):
                    return o
                if isinstance(o, dict):
                    for k in ("availability", "available", "spot", "trace", "values", "data"):
                        if k in o:
                            v = o[k]
                            if isinstance(v, list):
                                return v
                    for k, v in o.items():
                        if isinstance(v, list) and v and not isinstance(v[0], (dict, list)):
                            return v
                        if isinstance(v, list) and v and isinstance(v[0], dict):
                            # try dicts with availability-like field
                            for kk in ("availability", "available", "spot", "value", "v"):
                                if kk in v[0]:
                                    return [it.get(kk, 0) for it in v]
                return None

            seq = extract(obj)
            if seq is None:
                return []
            if seq and isinstance(seq[0], (list, tuple)) and len(seq[0]) >= 2:
                return [_coerce_to_01(it[1]) for it in seq]
            if seq and isinstance(seq[0], dict):
                for kk in ("availability", "available", "spot", "value", "v"):
                    if kk in seq[0]:
                        return [_coerce_to_01(it.get(kk, 0)) for it in seq]
                return []
            return [_coerce_to_01(v) for v in seq]
        except Exception:
            pass

    # Text/CSV
    out: List[int] = []
    try:
        with _open_maybe_gzip(path, "rt") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                if s[0] in "#;":
                    continue
                # split on comma / whitespace
                if "," in s:
                    parts = [p.strip() for p in s.split(",") if p.strip()]
                else:
                    parts = s.split()
                if not parts:
                    continue
                # skip header-like
                if not any(ch.isdigit() for ch in parts[-1]) and parts[-1].lower() not in ("true", "false", "t", "f", "yes", "no", "on", "off"):
                    continue
                out.append(_coerce_to_01(parts[-1]))
    except Exception:
        return []
    return out


class Solution(MultiRegionStrategy):
    NAME = "trace_aware_greedy_v1"

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

        self._trace_files = list(config.get("trace_files", [])) if isinstance(config, dict) else []
        self._raw_traces: List[List[int]] = []
        for p in self._trace_files:
            self._raw_traces.append(_load_trace_file(p))

        self._prepared = False
        self._have_traces = any(len(t) > 0 for t in self._raw_traces)

        self._avail: List[bytearray] = []
        self._runlen: List[array] = []
        self._nextspot: List[array] = []
        self._n_steps = 0
        self._gap = 0.0

        self._force_od = False

        self._done_sum = 0.0
        self._done_len = 0

        self._min_work_after_restart = 1.0
        self._od_buffer = 0.0

        return self

    def _ensure_prepared(self) -> None:
        if self._prepared:
            return
        self._prepared = True

        try:
            self._gap = float(self.env.gap_seconds)
        except Exception:
            self._gap = 1.0

        if self._gap <= 0:
            self._gap = 1.0

        self._n_steps = int(math.ceil(float(self.deadline) / self._gap)) + 2
        if self._n_steps < 4:
            self._n_steps = 4

        self._min_work_after_restart = max(1.0, min(self._gap * 0.20, 300.0))
        self._od_buffer = self._gap + float(self.restart_overhead)

        if not self._have_traces:
            return

        try:
            num_regions = int(self.env.get_num_regions())
        except Exception:
            num_regions = len(self._raw_traces)

        if num_regions <= 0:
            return

        raw = self._raw_traces
        if len(raw) < num_regions:
            raw = raw + [[] for _ in range(num_regions - len(raw))]
        elif len(raw) > num_regions:
            raw = raw[:num_regions]

        self._avail = []
        self._runlen = []
        self._nextspot = []

        for r in range(num_regions):
            aligned = self._align_trace(raw[r], self._n_steps)
            ba = bytearray(aligned)
            rl, ns = self._compute_runlen_nextspot(ba)
            self._avail.append(ba)
            self._runlen.append(rl)
            self._nextspot.append(ns)

    @staticmethod
    def _align_trace(raw: List[int], n_steps: int) -> List[int]:
        if n_steps <= 0:
            return []
        if not raw:
            return [0] * n_steps

        m = len(raw)
        if m == n_steps:
            return [1 if v else 0 for v in raw]

        # If raw longer, try downsample safely if divisible, else truncate.
        if m > n_steps:
            if m % n_steps == 0:
                k = m // n_steps
                out = [0] * n_steps
                idx = 0
                for i in range(n_steps):
                    seg_all = 1
                    end = idx + k
                    for j in range(idx, end):
                        if raw[j] == 0:
                            seg_all = 0
                            break
                    out[i] = seg_all
                    idx = end
                return out
            return [1 if v else 0 for v in raw[:n_steps]]

        # If raw shorter, try upsample if divisible, else pad with last.
        if n_steps % m == 0:
            k = n_steps // m
            out = [0] * n_steps
            p = 0
            for v in raw:
                vv = 1 if v else 0
                for _ in range(k):
                    out[p] = vv
                    p += 1
            return out

        out = [1 if v else 0 for v in raw]
        last = out[-1]
        if len(out) < n_steps:
            out.extend([last] * (n_steps - len(out)))
        else:
            out = out[:n_steps]
        return out

    @staticmethod
    def _compute_runlen_nextspot(av: bytearray) -> Tuple[array, array]:
        n = len(av)
        rl = array("I", [0]) * n
        ns = array("I", [n]) * n
        next_idx = n
        run = 0
        for i in range(n - 1, -1, -1):
            if av[i]:
                run += 1
                next_idx = i
                rl[i] = run
                ns[i] = i
            else:
                run = 0
                ns[i] = next_idx
        return rl, ns

    def _update_done_sum(self) -> None:
        td = self.task_done_time
        l = len(td)
        if l <= self._done_len:
            return
        inc = 0.0
        for v in td[self._done_len : l]:
            inc += float(v)
        self._done_sum += inc
        self._done_len = l

    def _spot_now_other_region(self, region: int, step_idx: int) -> Optional[bool]:
        env = self.env

        for name in ("get_has_spot", "is_spot_available", "get_spot_availability", "spot_available"):
            attr = getattr(env, name, None)
            if callable(attr):
                try:
                    return bool(attr(region))
                except TypeError:
                    pass
                except Exception:
                    pass

        for name in ("has_spot_by_region", "spot_by_region", "spot_available_by_region"):
            attr = getattr(env, name, None)
            if attr is not None:
                try:
                    return bool(attr[region])
                except Exception:
                    pass

        try:
            attr = getattr(env, "spot_availability", None)
            if attr is not None:
                return bool(attr[region][step_idx])
        except Exception:
            pass

        if self._have_traces and self._avail and 0 <= region < len(self._avail) and 0 <= step_idx < len(self._avail[region]):
            return bool(self._avail[region][step_idx])

        return None

    def _spot_now(self, region: int, step_idx: int, cur_region: int, cur_has_spot: bool) -> bool:
        if region == cur_region:
            return bool(cur_has_spot)
        v = self._spot_now_other_region(region, step_idx)
        return bool(v) if v is not None else False

    def _runlen_at(self, region: int, step_idx: int) -> int:
        if self._runlen and 0 <= region < len(self._runlen) and 0 <= step_idx < len(self._runlen[region]):
            return int(self._runlen[region][step_idx])
        return 0

    def _window_worth_switch(self, window_steps: int, last_cluster_type: ClusterType) -> bool:
        if window_steps <= 0:
            return False
        wall = window_steps * self._gap
        net = wall - float(self.restart_overhead)
        if last_cluster_type == ClusterType.ON_DEMAND:
            net -= float(self.restart_overhead)
        return net >= self._min_work_after_restart

    def _best_future_region_for_spot(self, cur_region: int, step_idx: int, num_regions: int) -> int:
        if not (self._nextspot and self._runlen):
            return cur_region
        best_r = cur_region
        best_next = 10**18
        best_run = -1
        for r in range(num_regions):
            try:
                nxt = int(self._nextspot[r][step_idx]) if step_idx < len(self._nextspot[r]) else 10**18
            except Exception:
                continue
            if nxt >= self._n_steps:
                continue
            try:
                run = int(self._runlen[r][nxt]) if nxt < len(self._runlen[r]) else 0
            except Exception:
                run = 0
            if (nxt < best_next) or (nxt == best_next and run > best_run):
                best_next = nxt
                best_run = run
                best_r = r
        return best_r

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_prepared()
        self._update_done_sum()

        work_left = float(self.task_duration) - float(self._done_sum)
        if work_left <= 0:
            return ClusterType.NONE

        t = float(self.env.elapsed_seconds)
        time_left = float(self.deadline) - t
        if time_left <= 0:
            return ClusterType.NONE

        try:
            cur_region = int(self.env.get_current_region())
        except Exception:
            cur_region = 0
        try:
            num_regions = int(self.env.get_num_regions())
        except Exception:
            num_regions = len(self._avail) if self._avail else 1
        if num_regions <= 0:
            num_regions = 1

        step_idx = int(t // self._gap) if self._gap > 0 else 0
        if step_idx < 0:
            step_idx = 0

        if self._force_od:
            return ClusterType.ON_DEMAND

        overhead_needed_od = float(self.remaining_restart_overhead) if last_cluster_type == ClusterType.ON_DEMAND else float(self.restart_overhead)
        required_od = overhead_needed_od + work_left

        if time_left <= required_od + self._od_buffer:
            self._force_od = True
            return ClusterType.ON_DEMAND

        if float(self.remaining_restart_overhead) > 0.0:
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            # last NONE while overhead pending: pay overhead if we can cheaply, else wait if slack
            if has_spot:
                return ClusterType.SPOT
            # if can safely idle a step, do it; otherwise OD
            if time_left - self._gap > required_od + self._od_buffer:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        # No pending overhead
        # If spot in current region, usually take it (cheap). Avoid if window too short and coming from OD.
        if has_spot:
            if self._have_traces and self._runlen:
                window = self._runlen_at(cur_region, step_idx)
                if last_cluster_type == ClusterType.ON_DEMAND and not self._window_worth_switch(window, last_cluster_type):
                    return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # Spot not in current region: search other regions with spot now.
        best_r = -1
        best_window = -1
        if num_regions > 1:
            for r in range(num_regions):
                if r == cur_region:
                    continue
                if not self._spot_now(r, step_idx, cur_region, has_spot):
                    continue
                window = self._runlen_at(r, step_idx) if (self._have_traces and self._runlen) else 1
                if window > best_window:
                    best_window = window
                    best_r = r

        if best_r >= 0:
            window = best_window if best_window >= 0 else 1
            if self._window_worth_switch(window, last_cluster_type):
                try:
                    self.env.switch_region(best_r)
                except Exception:
                    pass
                return ClusterType.SPOT

        # No spot anywhere (or not worth switching): idle if slack, else use OD.
        if time_left - self._gap > required_od + self._od_buffer:
            if num_regions > 1:
                target = self._best_future_region_for_spot(cur_region, step_idx, num_regions)
                if target != cur_region:
                    try:
                        self.env.switch_region(target)
                    except Exception:
                        pass
            return ClusterType.NONE

        return ClusterType.ON_DEMAND