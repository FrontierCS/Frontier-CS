import json
import math
import os
import pickle
import gzip
from argparse import Namespace
from array import array
from typing import Any, List, Optional, Sequence, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_trace_greedy_v1"

    # Given in the problem statement (used only for heuristics / thresholds).
    _SPOT_RATE = 0.9701
    _OD_RATE = 3.06

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path, "r") as f:
            config = json.load(f)

        self._trace_files = list(config.get("trace_files", []))

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self._lazy_inited = False
        self._use_traces = False
        self._switching_enabled = False

        self._avail = None
        self._runlen = None
        self._best_region = None
        self._steps = 0

        self._done_sum = 0.0
        self._done_len = 0

        self._trace_obs = 0
        self._trace_match = 0

        self._buffer_seconds = 0.0
        self._min_run_none_to_spot = 0.0
        self._min_run_spot_to_spot = 0.0
        self._min_run_od_to_spot = 0.0
        self._switch_advantage_seconds = 0.0

        return self

    @staticmethod
    def _maybe_open(path: str):
        if path.endswith(".gz"):
            return gzip.open(path, "rb")
        return open(path, "rb")

    @staticmethod
    def _extract_series(obj: Any) -> Optional[Sequence]:
        if obj is None:
            return None
        if isinstance(obj, (list, tuple)):
            return obj
        if isinstance(obj, dict):
            for k in ("trace", "availability", "avail", "spot", "has_spot", "data", "values", "series", "arr", "array"):
                v = obj.get(k, None)
                if isinstance(v, (list, tuple)):
                    return v
            # Fall back: first list-like value in dict
            for v in obj.values():
                if isinstance(v, (list, tuple)):
                    return v
        return None

    @staticmethod
    def _to_bool_list(seq: Sequence) -> List[int]:
        out: List[int] = []
        for x in seq:
            if isinstance(x, bool):
                out.append(1 if x else 0)
                continue
            if isinstance(x, (int, float)):
                out.append(1 if x > 0 else 0)
                continue
            if isinstance(x, str):
                s = x.strip().lower()
                if s in ("1", "true", "t", "yes", "y", "on"):
                    out.append(1)
                elif s in ("0", "false", "f", "no", "n", "off", ""):
                    out.append(0)
                else:
                    try:
                        out.append(1 if float(s) > 0 else 0)
                    except Exception:
                        out.append(0)
                continue
            if isinstance(x, dict):
                for k in ("has_spot", "spot", "available", "avail", "value", "v"):
                    if k in x:
                        try:
                            out.append(1 if float(x[k]) > 0 else 0)
                        except Exception:
                            out.append(1 if bool(x[k]) else 0)
                        break
                else:
                    out.append(0)
                continue
            out.append(1 if x else 0)
        return out

    def _read_trace_file(self, path: str) -> Optional[List[int]]:
        if not path or not os.path.exists(path):
            return None

        lower = path.lower()
        try:
            if lower.endswith(".npy") or lower.endswith(".npz"):
                try:
                    import numpy as np  # type: ignore
                except Exception:
                    np = None
                if np is None:
                    return None
                if lower.endswith(".npy"):
                    arr = np.load(path, allow_pickle=True)
                    if hasattr(arr, "tolist"):
                        return self._to_bool_list(arr.tolist())
                    return self._to_bool_list(list(arr))
                else:
                    z = np.load(path, allow_pickle=True)
                    keys = list(getattr(z, "files", []))
                    if keys:
                        arr = z[keys[0]]
                        if hasattr(arr, "tolist"):
                            return self._to_bool_list(arr.tolist())
                        return self._to_bool_list(list(arr))
                    return None

            if lower.endswith(".pkl") or lower.endswith(".pickle"):
                with self._maybe_open(path) as f:
                    obj = pickle.load(f)
                seq = self._extract_series(obj)
                if seq is None:
                    return None
                return self._to_bool_list(seq)

            # Try JSON first if it looks like JSON.
            with self._maybe_open(path) as f:
                raw = f.read()
            stripped = raw.lstrip()
            if stripped.startswith(b"{") or stripped.startswith(b"["):
                try:
                    obj = json.loads(raw.decode("utf-8"))
                    seq = self._extract_series(obj)
                    if seq is None and isinstance(obj, list):
                        seq = obj
                    if seq is None:
                        return None
                    return self._to_bool_list(seq)
                except Exception:
                    pass

            # Plain text: split by whitespace / commas.
            text = raw.decode("utf-8", errors="ignore")
            toks: List[str] = []
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "," in line:
                    toks.extend([t.strip() for t in line.split(",") if t.strip() != ""])
                else:
                    toks.extend([t for t in line.split() if t != ""])
            if not toks:
                return None
            return self._to_bool_list(toks)
        except Exception:
            return None

    def _resample_to_steps(self, series: Sequence[int], steps: int) -> bytearray:
        n = len(series)
        if n <= 0:
            return bytearray(steps)
        if n == steps:
            return bytearray(int(x) & 1 for x in series)

        out = bytearray(steps)
        # Map each step to a source index; nearest-neighbor.
        for i in range(steps):
            j = int((i * n) // steps)
            if j >= n:
                j = n - 1
            out[i] = 1 if series[j] else 0
        return out

    def _lazy_init(self) -> None:
        if self._lazy_inited:
            return
        self._lazy_inited = True

        g = float(getattr(self.env, "gap_seconds", 1.0))
        if g <= 0:
            g = 1.0
        steps = int(math.ceil(self.deadline / g)) + 2
        self._steps = steps

        self._buffer_seconds = max(1e-6, min(0.5 * self.restart_overhead, 0.25 * g))
        # Heuristic thresholds (in seconds).
        o = self.restart_overhead
        od = self._OD_RATE
        sp = self._SPOT_RATE
        if od > sp:
            self._min_run_od_to_spot = max(o * 1.2, (2.0 * o * od) / (od - sp))
        else:
            self._min_run_od_to_spot = o * 2.0
        self._min_run_none_to_spot = max(o * 1.1, 2.0 * g)
        self._min_run_spot_to_spot = max(o * 1.1, 2.0 * g)
        self._switch_advantage_seconds = max(o, 5.0 * g)

        num_regions = int(self.env.get_num_regions())
        if not self._trace_files or num_regions <= 0:
            self._use_traces = False
            self._switching_enabled = False
            return

        avail: List[bytearray] = []
        for r in range(num_regions):
            path = self._trace_files[r] if r < len(self._trace_files) else None
            series = self._read_trace_file(path) if path else None
            if series is None:
                avail.append(bytearray(steps))
                continue
            avail.append(self._resample_to_steps(series, steps))

        runlen: List[array] = []
        for r in range(num_regions):
            rl = array("I", [0]) * steps
            a = avail[r]
            nxt = 0
            for i in range(steps - 1, -1, -1):
                if a[i]:
                    nxt += 1
                    rl[i] = nxt
                else:
                    nxt = 0
                    rl[i] = 0
            runlen.append(rl)

        best_region = array("h", [-1]) * steps
        for i in range(steps):
            br = -1
            bl = 0
            for r in range(num_regions):
                l = runlen[r][i]
                if l > bl:
                    bl = l
                    br = r
            best_region[i] = br

        self._avail = avail
        self._runlen = runlen
        self._best_region = best_region

        self._use_traces = True
        self._switching_enabled = False  # enabled after a few consistency checks

    def _update_done_sum(self) -> float:
        td = self.task_done_time
        l = len(td)
        if l > self._done_len:
            self._done_sum += float(sum(td[self._done_len:l]))
            self._done_len = l
        return self._done_sum

    def _update_trace_confidence(self, predicted: bool, observed: bool) -> None:
        self._trace_obs += 1
        if predicted == observed:
            self._trace_match += 1

        if self._trace_obs >= 3:
            ratio = self._trace_match / self._trace_obs
            if ratio < 0.34:
                self._use_traces = False
                self._switching_enabled = False
            elif ratio >= 0.67:
                self._switching_enabled = True

        if self._trace_obs >= 20:
            ratio = self._trace_match / self._trace_obs
            if ratio < 0.80:
                self._use_traces = False
                self._switching_enabled = False
            else:
                self._switching_enabled = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        g = float(self.env.gap_seconds)
        if g <= 0:
            g = 1.0

        i = int(self.env.elapsed_seconds / g + 1e-9)
        if i < 0:
            i = 0

        done = self._update_done_sum()
        work_rem = float(self.task_duration - done)
        if work_rem <= 1e-9:
            return ClusterType.NONE

        time_left = float(self.deadline - self.env.elapsed_seconds)
        o = float(self.restart_overhead)
        buf = float(self._buffer_seconds)

        # If restart overhead is currently pending, avoid switches that reset it.
        if getattr(self, "remaining_restart_overhead", 0.0) > 1e-9:
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            if last_cluster_type == ClusterType.SPOT and has_spot:
                return ClusterType.SPOT
            # Cannot run spot; switching will reset overhead anyway. Use on-demand if needed, else wait.
            if time_left <= (work_rem + o + buf):
                return ClusterType.ON_DEMAND
            if time_left - g > (work_rem + o + buf):
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        # Conservative "can I still finish if I start/continue on-demand now?"
        if last_cluster_type == ClusterType.ON_DEMAND:
            needed_od = work_rem
        else:
            needed_od = work_rem + o

        if time_left <= needed_od + buf:
            return ClusterType.ON_DEMAND

        # If traces are unusable, don't switch regions.
        if not self._use_traces or self._avail is None or self._runlen is None or self._best_region is None:
            if has_spot:
                # Switch OD->SPOT only if plenty of slack.
                if last_cluster_type == ClusterType.ON_DEMAND:
                    if time_left - (work_rem + o) > (2.0 * o + buf):
                        return ClusterType.SPOT
                    return ClusterType.ON_DEMAND
                return ClusterType.SPOT

            # No spot: wait if safe, else on-demand.
            if time_left - g > (work_rem + o + buf):
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        num_regions = int(self.env.get_num_regions())
        rcur = int(self.env.get_current_region())
        if i >= self._steps:
            # Out of trace horizon: fall back.
            if has_spot:
                return ClusterType.SPOT
            if time_left - g > (work_rem + o + buf):
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        # Update trace confidence using current region only.
        predicted_cur = bool(self._avail[rcur][i]) if 0 <= rcur < num_regions else False
        self._update_trace_confidence(predicted_cur, has_spot)
        if not self._use_traces:
            # Traces disabled due to mismatch; fall back.
            if has_spot:
                if last_cluster_type == ClusterType.ON_DEMAND:
                    if time_left - (work_rem + o) > (2.0 * o + buf):
                        return ClusterType.SPOT
                    return ClusterType.ON_DEMAND
                return ClusterType.SPOT
            if time_left - g > (work_rem + o + buf):
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        rbest = int(self._best_region[i])
        have_any_spot = (rbest >= 0)

        # If we can run spot in the current region, prefer staying on spot (cheap, avoids overhead).
        if has_spot:
            if last_cluster_type == ClusterType.SPOT:
                # Optionally switch to a much better region (only if traces are trusted).
                if self._switching_enabled and have_any_spot and rbest != rcur:
                    run_cur = float(self._runlen[rcur][i]) * g
                    run_best = float(self._runlen[rbest][i]) * g
                    if run_best >= self._min_run_spot_to_spot and (run_best - run_cur) > self._switch_advantage_seconds:
                        self.env.switch_region(rbest)
                        return ClusterType.SPOT
                return ClusterType.SPOT

            # Currently not on spot: switch to spot only if it is likely worth it.
            if last_cluster_type == ClusterType.ON_DEMAND:
                if have_any_spot:
                    run_best = float(self._runlen[rbest][i]) * g
                    slack_vs_od = time_left - needed_od
                    if slack_vs_od > (2.0 * o + buf) and run_best >= self._min_run_od_to_spot:
                        if self._switching_enabled and rbest != rcur:
                            self.env.switch_region(rbest)
                        return ClusterType.SPOT
                return ClusterType.ON_DEMAND

            # last was NONE
            if have_any_spot:
                run_best = float(self._runlen[rbest][i]) * g
                if run_best >= self._min_run_none_to_spot and (time_left - g) > (work_rem + o + buf):
                    if self._switching_enabled and rbest != rcur:
                        self.env.switch_region(rbest)
                    return ClusterType.SPOT
            return ClusterType.SPOT

        # No spot in current region.
        if have_any_spot:
            run_best = float(self._runlen[rbest][i]) * g
            if run_best >= self._min_run_spot_to_spot and (time_left - g) > (work_rem + o + buf):
                if self._switching_enabled and rbest != rcur:
                    self.env.switch_region(rbest)
                    return ClusterType.SPOT
                # If best is current (shouldn't happen since has_spot False), do not risk SPOT.
            # Otherwise, decide between waiting and on-demand.
            if time_left - g > (work_rem + o + buf):
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        # No spot anywhere (per traces): wait if safe, else on-demand.
        if time_left - g > (work_rem + o + buf):
            return ClusterType.NONE
        return ClusterType.ON_DEMAND