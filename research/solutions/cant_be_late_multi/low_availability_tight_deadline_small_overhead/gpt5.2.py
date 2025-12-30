import json
import math
import os
import pickle
from argparse import Namespace
from array import array

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path, "r") as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self._trace_files = list(config.get("trace_files", [])) if isinstance(config, dict) else []
        self._raw_traces = None  # list[bytearray] (un-resampled)
        self._prepared = False
        self._trace_ready = False
        self._trace_disabled = False
        self._trace_mismatch = 0

        self._spot_by_region = None  # list[bytearray] length=steps
        self._run_len_by_region = None  # list[array('I')] length=steps
        self._next_wait_by_region = None  # list[array('I')] length=steps
        self._best_region_now = None  # array('h') length=steps, -1 if none
        self._best_run_steps_now = None  # array('I') length=steps
        self._best_wait_region = None  # array('h') length=steps

        self._done_work = 0.0
        self._tdt_len = 0

        self._od_mode = False

        self._gap = None
        self._steps = None
        self._min_steps_positive_progress = None
        self._min_steps_switch_to_spot = None
        self._min_steps_od_to_spot = None
        self._idle_slack_buffer = None
        self._od_commit_slack = None
        self._od_to_spot_min_slack = None

        self._max_steps_load_hint = int(math.ceil(float(config["deadline"]) * 3600.0)) if isinstance(config, dict) and "deadline" in config else None

        return self

    @staticmethod
    def _safe_bool(x):
        if isinstance(x, bool):
            return x
        if isinstance(x, (int, float)):
            return x != 0
        if isinstance(x, str):
            s = x.strip().lower()
            if s in ("1", "true", "t", "yes", "y", "on", "available", "avail"):
                return True
            if s in ("0", "false", "f", "no", "n", "off", "unavailable", "unavail"):
                return False
            try:
                return float(s) != 0.0
            except Exception:
                return False
        return bool(x)

    def _get_current_has_spot(self, fallback: bool) -> bool:
        env = getattr(self, "env", None)
        if env is None:
            return bool(fallback)

        for name in ("has_spot", "spot_available", "spot_availability", "_has_spot"):
            if hasattr(env, name):
                val = getattr(env, name)
                try:
                    if callable(val):
                        val = val()
                except Exception:
                    pass
                if isinstance(val, (bool, int)):
                    return bool(val)

        for name in ("get_has_spot", "get_spot", "get_spot_availability", "spot"):
            if hasattr(env, name):
                meth = getattr(env, name)
                if callable(meth):
                    try:
                        val = meth()
                        if isinstance(val, (bool, int)):
                            return bool(val)
                    except Exception:
                        pass

        return bool(fallback)

    def _get_done_work(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            self._done_work = 0.0
            self._tdt_len = 0
            return 0.0
        n = len(tdt)
        if n == self._tdt_len:
            return self._done_work
        if n < self._tdt_len:
            self._done_work = 0.0
            self._tdt_len = 0
        if n == self._tdt_len + 1:
            self._done_work += float(tdt[-1])
        else:
            self._done_work += float(sum(tdt[self._tdt_len :]))
        self._tdt_len = n
        return self._done_work

    def _read_trace_file_to_bytearray(self, path: str, limit: int | None) -> bytearray:
        ext = os.path.splitext(path)[1].lower()
        if ext in (".npy", ".npz"):
            try:
                import numpy as np  # type: ignore

                if ext == ".npy":
                    arr = np.load(path, allow_pickle=False)
                else:
                    npz = np.load(path, allow_pickle=False)
                    keys = list(npz.keys())
                    arr = npz[keys[0]] if keys else np.array([], dtype=np.int8)
                arr = np.asarray(arr).ravel()
                n = int(arr.shape[0])
                if limit is not None:
                    n = min(n, int(limit))
                out = bytearray(n)
                if n > 0:
                    vals = arr[:n]
                    if vals.dtype.kind in ("b", "i", "u"):
                        for i in range(n):
                            out[i] = 1 if int(vals[i]) != 0 else 0
                    else:
                        for i in range(n):
                            out[i] = 1 if float(vals[i]) != 0.0 else 0
                return out
            except Exception:
                pass

        if ext in (".pkl", ".pickle"):
            try:
                with open(path, "rb") as f:
                    obj = pickle.load(f)
                seq = None
                if isinstance(obj, (list, tuple, bytearray, bytes)):
                    seq = obj
                elif isinstance(obj, dict):
                    for k in ("spot", "availability", "available", "trace", "data", "values"):
                        if k in obj and isinstance(obj[k], (list, tuple, bytearray, bytes)):
                            seq = obj[k]
                            break
                if seq is None:
                    return bytearray()
                out = bytearray()
                if isinstance(seq, (bytes, bytearray)):
                    if limit is None:
                        return bytearray(1 if b else 0 for b in seq)
                    return bytearray(1 if seq[i] else 0 for i in range(min(len(seq), limit)))
                for v in seq:
                    if limit is not None and len(out) >= limit:
                        break
                    out.append(1 if self._safe_bool(v) else 0)
                return out
            except Exception:
                pass

        if ext == ".json":
            try:
                with open(path, "r") as f:
                    obj = json.load(f)
                seq = None
                if isinstance(obj, list):
                    seq = obj
                elif isinstance(obj, dict):
                    for k in ("spot", "availability", "available", "trace", "data", "values"):
                        if k in obj and isinstance(obj[k], list):
                            seq = obj[k]
                            break
                if seq is None:
                    return bytearray()
                out = bytearray()
                for v in seq:
                    if limit is not None and len(out) >= limit:
                        break
                    if isinstance(v, (list, tuple)) and v:
                        out.append(1 if self._safe_bool(v[-1]) else 0)
                    elif isinstance(v, dict):
                        vv = None
                        for kk in ("spot", "available", "availability", "value", "v", "is_spot"):
                            if kk in v:
                                vv = v[kk]
                                break
                        out.append(1 if self._safe_bool(vv) else 0)
                    else:
                        out.append(1 if self._safe_bool(v) else 0)
                return out
            except Exception:
                pass

        out = bytearray()
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if limit is not None and len(out) >= limit:
                        break
                    s = line.strip()
                    if not s:
                        continue
                    if s[0] in ("#", "/"):
                        continue
                    if "," in s:
                        parts = [p.strip() for p in s.split(",") if p.strip() != ""]
                    else:
                        parts = s.split()
                    if not parts:
                        continue
                    val = None
                    if len(parts) >= 2:
                        for candidate in (parts[-1], parts[1], parts[0]):
                            try:
                                val = self._safe_bool(candidate)
                                break
                            except Exception:
                                continue
                    else:
                        try:
                            val = self._safe_bool(parts[0])
                        except Exception:
                            val = None
                    if val is None:
                        continue
                    out.append(1 if val else 0)
        except Exception:
            return bytearray()
        return out

    def _resample_trace(self, raw: bytearray, steps: int, gap_seconds: float, deadline_seconds: float) -> bytearray:
        if steps <= 0:
            return bytearray()

        n = len(raw)
        if n == 0:
            return bytearray(steps)

        if n == steps:
            return raw[:steps]

        gi = None
        if gap_seconds >= 1.0:
            rg = round(gap_seconds)
            if abs(gap_seconds - rg) < 1e-9:
                gi = int(rg)

        if gi is not None and gi > 1:
            approx_per_second = int(round(deadline_seconds))
            if abs(n - approx_per_second) <= max(2, int(0.001 * approx_per_second)):
                need = steps * gi
                if n >= need:
                    out = bytearray(steps)
                    j = 0
                    idx = 0
                    while j < steps and idx < n:
                        out[j] = raw[idx]
                        j += 1
                        idx += gi
                    return out

        if n > steps:
            return raw[:steps]

        out = bytearray(steps)
        out[:n] = raw
        return out

    def _ensure_prepared(self):
        if self._prepared:
            return
        if getattr(self, "env", None) is None:
            return

        self._gap = float(getattr(self.env, "gap_seconds", 1.0))
        if self._gap <= 0:
            self._gap = 1.0
        self._steps = int(math.ceil(float(self.deadline) / self._gap))
        if self._steps <= 0:
            self._steps = 1

        r_over = float(self.restart_overhead)
        g = self._gap

        self._min_steps_positive_progress = int(math.floor(r_over / g)) + 1
        self._min_steps_switch_to_spot = int(math.floor((r_over + g) / g)) + 1
        self._min_steps_od_to_spot = int(math.floor((4.0 * r_over + g) / g)) + 1

        self._od_commit_slack = max(10.0 * r_over, 60.0 * g)
        self._idle_slack_buffer = max(14.0 * r_over, 180.0 * g)
        self._od_to_spot_min_slack = max(30.0 * r_over, 600.0 * g)

        self._prepared = True

    def _ensure_trace_ready(self):
        if self._trace_ready or self._trace_disabled:
            return
        self._ensure_prepared()
        if not self._prepared or getattr(self, "env", None) is None:
            return

        num_regions = int(self.env.get_num_regions())
        if num_regions <= 0:
            self._trace_disabled = True
            return

        if not self._trace_files or len(self._trace_files) < num_regions:
            self._trace_disabled = True
            return

        deadline_seconds = float(self.deadline)
        steps = int(self._steps)
        limit_load = self._max_steps_load_hint
        if limit_load is None or limit_load <= 0:
            limit_load = int(max(steps, 1))

        raw_traces = []
        try:
            for i in range(num_regions):
                path = self._trace_files[i]
                raw = self._read_trace_file_to_bytearray(path, limit=limit_load)
                raw_traces.append(raw)
        except Exception:
            self._trace_disabled = True
            return

        spot_by_region = []
        for i in range(num_regions):
            spot_by_region.append(self._resample_trace(raw_traces[i], steps, self._gap, deadline_seconds))

        run_len_by_region = []
        next_wait_by_region = []
        BIG = steps + 5

        for r in range(num_regions):
            spot = spot_by_region[r]
            rl = array("I", [0]) * steps
            nw = array("I", [0]) * steps
            nextw = BIG
            rnext = 0
            for t in range(steps - 1, -1, -1):
                if spot[t]:
                    rnext = 1 + (rnext if t + 1 < steps else 0)
                    rl[t] = rnext
                    nextw = 0
                    nw[t] = 0
                else:
                    rnext = 0
                    rl[t] = 0
                    nextw = 1 + (nextw if t + 1 < steps else BIG)
                    nw[t] = nextw
            run_len_by_region.append(rl)
            next_wait_by_region.append(nw)

        best_region_now = array("h", [-1]) * steps
        best_run_steps = array("I", [0]) * steps
        best_wait_region = array("h", [0]) * steps

        for t in range(steps):
            br = -1
            brl = 0
            for r in range(num_regions):
                if spot_by_region[r][t]:
                    rl = run_len_by_region[r][t]
                    if rl > brl:
                        brl = rl
                        br = r
            best_region_now[t] = br
            best_run_steps[t] = brl

            bw = 0
            bwv = BIG
            for r in range(num_regions):
                w = next_wait_by_region[r][t]
                if w < bwv:
                    bwv = w
                    bw = r
            best_wait_region[t] = bw

        self._raw_traces = raw_traces
        self._spot_by_region = spot_by_region
        self._run_len_by_region = run_len_by_region
        self._next_wait_by_region = next_wait_by_region
        self._best_region_now = best_region_now
        self._best_run_steps_now = best_run_steps
        self._best_wait_region = best_wait_region

        self._trace_ready = True
        self._trace_disabled = False
        self._trace_mismatch = 0

    def _time_index(self) -> int:
        g = self._gap if self._gap is not None else float(getattr(self.env, "gap_seconds", 1.0))
        if g <= 0:
            g = 1.0
        t = int(float(self.env.elapsed_seconds) / g + 1e-9)
        if self._steps is not None:
            if t < 0:
                t = 0
            elif t >= self._steps:
                t = self._steps - 1
        else:
            if t < 0:
                t = 0
        return t

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_prepared()
        self._ensure_trace_ready()

        done = self._get_done_work()
        remaining_work = float(self.task_duration) - float(done)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = float(self.env.elapsed_seconds)
        remaining_time = float(self.deadline) - elapsed
        if remaining_time <= 0.0:
            return ClusterType.NONE

        raw_slack = remaining_time - remaining_work
        pending_overhead = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        slack = raw_slack - pending_overhead

        if (not self._od_mode) and (slack <= self._od_commit_slack):
            self._od_mode = True

        cur_region = int(self.env.get_current_region())
        cur_has_spot = self._get_current_has_spot(has_spot)

        if self._trace_ready and not self._trace_disabled:
            t = self._time_index()
            try:
                pred = bool(self._spot_by_region[cur_region][t])
                if pred != bool(cur_has_spot):
                    self._trace_mismatch += 1
                    if self._trace_mismatch > 25:
                        self._trace_disabled = True
            except Exception:
                self._trace_disabled = True

        if self._od_mode:
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.SPOT and cur_has_spot:
            return ClusterType.SPOT

        t = self._time_index()

        if last_cluster_type == ClusterType.ON_DEMAND:
            if self._trace_ready and not self._trace_disabled:
                br = int(self._best_region_now[t])
                if br >= 0:
                    run_steps = int(self._run_len_by_region[br][t])
                    if slack >= self._od_to_spot_min_slack and run_steps >= self._min_steps_od_to_spot:
                        if br != cur_region:
                            self.env.switch_region(br)
                        if self._get_current_has_spot(False):
                            return ClusterType.SPOT
            if cur_has_spot and slack >= self._od_to_spot_min_slack:
                return ClusterType.SPOT
            if slack > self._idle_slack_buffer:
                return ClusterType.NONE
            if slack <= self._od_commit_slack:
                self._od_mode = True
            return ClusterType.ON_DEMAND

        if cur_has_spot:
            if self._trace_ready and not self._trace_disabled:
                run_steps_here = int(self._run_len_by_region[cur_region][t])
                if last_cluster_type != ClusterType.SPOT and run_steps_here < self._min_steps_positive_progress and slack > self._idle_slack_buffer:
                    return ClusterType.NONE
            return ClusterType.SPOT

        if self._trace_ready and not self._trace_disabled:
            br = int(self._best_region_now[t])
            if br >= 0:
                run_steps = int(self._run_len_by_region[br][t])
                if run_steps >= self._min_steps_switch_to_spot:
                    if br != cur_region:
                        self.env.switch_region(br)
                    if self._get_current_has_spot(False):
                        return ClusterType.SPOT

            if slack > self._idle_slack_buffer:
                bw = int(self._best_wait_region[t])
                if bw != cur_region:
                    self.env.switch_region(bw)
                return ClusterType.NONE

            if slack <= self._od_commit_slack:
                self._od_mode = True
            return ClusterType.ON_DEMAND

        if slack > self._idle_slack_buffer:
            return ClusterType.NONE

        if slack <= self._od_commit_slack:
            self._od_mode = True
        return ClusterType.ON_DEMAND