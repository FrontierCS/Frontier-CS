import os
import json
import math
from argparse import Namespace
from array import array
from typing import List, Optional, Sequence

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _get_ct_none():
    if hasattr(ClusterType, "NONE"):
        return ClusterType.NONE
    if hasattr(ClusterType, "None"):
        return getattr(ClusterType, "None")
    for name in ("NO_CLUSTER", "NULL", "EMPTY"):
        if hasattr(ClusterType, name):
            return getattr(ClusterType, name)
    return None


_CT_NONE = _get_ct_none()


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_v1"

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

        base_dir = os.path.dirname(os.path.abspath(spec_path))
        trace_files = config.get("trace_files", []) or []
        self._trace_files = [
            (p if os.path.isabs(p) else os.path.join(base_dir, p)) for p in trace_files
        ]

        self._raw_traces: List[bytearray] = []
        for p in self._trace_files:
            self._raw_traces.append(self._load_trace_file(p))

        self._precomputed = False
        self._gap = None
        self._steps = None
        self._num_regions = None

        self._avail: List[memoryview] = []
        self._run_len: List[array] = []
        self._any_spot: Optional[bytearray] = None
        self._best_region: Optional[array] = None
        self._best_run: Optional[array] = None
        self._next_any_spot: Optional[array] = None

        self._committed_region: Optional[int] = None
        self._commit_until: int = 0

        self._done_sum: float = 0.0
        self._last_done_len: int = 0

        self._idle_slack_min: float = 0.0
        self._switch_slack_min: float = 0.0
        self._finish_spot_run_need: float = 0.0

        return self

    @staticmethod
    def _tok_to_bit(tok: str) -> Optional[int]:
        if not tok:
            return None
        c = tok[0]
        if c in ("1", "T", "t", "Y", "y"):
            return 1
        if c in ("0", "F", "f", "N", "n"):
            return 0
        try:
            return 1 if float(tok) > 0.5 else 0
        except Exception:
            return None

    def _load_trace_file(self, path: str) -> bytearray:
        ext = os.path.splitext(path)[1].lower()
        if ext in (".npy", ".npz"):
            try:
                import numpy as np  # type: ignore

                obj = np.load(path, allow_pickle=False)
                if hasattr(obj, "files"):
                    key = obj.files[0]
                    arr = obj[key]
                else:
                    arr = obj
                arr = arr.astype("uint8", copy=False).ravel()
                return bytearray((1 if int(x) else 0) for x in arr.tolist())
            except Exception:
                pass

        if ext == ".json":
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    for k in ("availability", "trace", "data", "spot"):
                        if k in data and isinstance(data[k], list):
                            data = data[k]
                            break
                if isinstance(data, list):
                    out = bytearray()
                    out_extend = out.extend
                    chunk = bytearray()
                    for v in data:
                        if isinstance(v, bool):
                            chunk.append(1 if v else 0)
                        elif isinstance(v, (int, float)):
                            chunk.append(1 if v else 0)
                        elif isinstance(v, str):
                            b = self._tok_to_bit(v.strip())
                            if b is not None:
                                chunk.append(b)
                        if len(chunk) >= 65536:
                            out_extend(chunk)
                            chunk.clear()
                    if chunk:
                        out_extend(chunk)
                    return out
            except Exception:
                pass

        out = bytearray()
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line[0] == "#":
                    continue
                s = line.replace(",", " ")
                parts = s.split()
                if not parts:
                    continue
                tok = parts[-1]
                b = self._tok_to_bit(tok)
                if b is None and len(parts) >= 2:
                    b = self._tok_to_bit(parts[0])
                if b is None:
                    continue
                out.append(b)
        return out

    @staticmethod
    def _downsample(raw: Sequence[int], target_len: int) -> bytearray:
        L = len(raw)
        if target_len <= 0:
            return bytearray()
        if L == 0:
            return bytearray([0]) * target_len
        if L == target_len:
            return bytearray(raw)
        out = bytearray(target_len)
        if L > target_len and (L % target_len == 0):
            factor = L // target_len
            idx = 0
            for i in range(target_len):
                out[i] = 1 if raw[idx] else 0
                idx += factor
            return out
        for i in range(target_len):
            j = (i * L) // target_len
            out[i] = 1 if raw[j] else 0
        return out

    def _ensure_precomputed(self, has_spot: bool) -> None:
        if self._precomputed:
            return

        self._gap = float(self.env.gap_seconds)
        gap = self._gap
        steps = int(math.ceil(self.deadline / gap)) + 1
        self._steps = steps
        R = int(self.env.get_num_regions())
        self._num_regions = R

        avail_list: List[memoryview] = []
        for r in range(R):
            if r < len(self._raw_traces):
                raw = self._raw_traces[r]
                ds = self._downsample(raw, steps)
            else:
                ds = bytearray([0]) * steps
            avail_list.append(memoryview(ds))
        self._avail = avail_list

        run_len_list: List[array] = []
        for r in range(R):
            runs = array("I", [0]) * (steps + 1)
            av = avail_list[r]
            nxt = 0
            for t in range(steps - 1, -1, -1):
                if av[t]:
                    nxt = nxt + 1
                    runs[t] = nxt
                else:
                    nxt = 0
                    runs[t] = 0
            run_len_list.append(runs)
        self._run_len = run_len_list

        any_spot = bytearray(steps)
        best_region = array("b", [-1]) * steps
        best_run = array("I", [0]) * steps

        for t in range(steps):
            br = -1
            brlen = 0
            anyv = 0
            for r in range(R):
                if avail_list[r][t]:
                    anyv = 1
                    rl = run_len_list[r][t]
                    if rl > brlen:
                        brlen = rl
                        br = r
            any_spot[t] = anyv
            best_region[t] = br
            best_run[t] = brlen

        next_any = array("I", [steps]) * (steps + 1)
        next_any[steps] = steps
        nxt = steps
        for t in range(steps - 1, -1, -1):
            if any_spot[t]:
                nxt = t
            next_any[t] = nxt

        self._any_spot = any_spot
        self._best_region = best_region
        self._best_run = best_run
        self._next_any_spot = next_any

        ro = float(self.restart_overhead)
        self._idle_slack_min = max(2.0 * gap, 4.0 * ro)
        self._switch_slack_min = max(2.0 * ro, gap)
        self._finish_spot_run_need = ro + gap

        self._precomputed = True

    def _update_done_sum(self) -> None:
        lst = self.task_done_time
        n = len(lst)
        i = self._last_done_len
        if n <= i:
            return
        s = self._done_sum
        for k in range(i, n):
            s += float(lst[k])
        self._done_sum = s
        self._last_done_len = n

    def _spot_avail(self, region: int, step: int, has_spot: bool) -> bool:
        if region < 0 or region >= self._num_regions:
            return False
        if step < 0:
            step = 0
        if step >= self._steps:
            step = self._steps - 1
        try:
            return bool(self._avail[region][step])
        except Exception:
            return bool(has_spot)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_precomputed(has_spot)
        self._update_done_sum()

        if self._done_sum >= float(self.task_duration) - 1e-9:
            return _CT_NONE

        elapsed = float(self.env.elapsed_seconds)
        if elapsed >= float(self.deadline) - 1e-9:
            return _CT_NONE

        gap = self._gap
        step = int(elapsed // gap)
        if step < 0:
            step = 0
        if step >= self._steps:
            step = self._steps - 1

        remaining_work = float(self.task_duration) - self._done_sum
        remaining_time = float(self.deadline) - elapsed
        slack = remaining_time - remaining_work

        cur_region = int(self.env.get_current_region())

        if getattr(self, "remaining_restart_overhead", 0.0) > 1e-9:
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            if last_cluster_type == ClusterType.SPOT and self._spot_avail(cur_region, step, has_spot):
                return ClusterType.SPOT

        any_spot_now = bool(self._any_spot[step])

        if any_spot_now:
            if self._committed_region is None or step >= self._commit_until or not self._spot_avail(self._committed_region, step, has_spot):
                r = int(self._best_region[step])
                if r < 0:
                    self._committed_region = None
                    self._commit_until = step
                else:
                    self._committed_region = r
                    self._commit_until = step + int(self._run_len[r][step])

            target = self._committed_region
            if target is not None and target >= 0:
                if cur_region != target:
                    self.env.switch_region(target)
                    cur_region = target
                if self._spot_avail(cur_region, step, has_spot):
                    if last_cluster_type == ClusterType.ON_DEMAND and slack < self._switch_slack_min:
                        return ClusterType.ON_DEMAND
                    if slack < -1e-6:
                        return ClusterType.ON_DEMAND
                    if slack <= 0.0:
                        run_seconds = float(self._run_len[cur_region][step]) * gap
                        if run_seconds + 1e-9 >= remaining_work + self._finish_spot_run_need:
                            return ClusterType.SPOT
                        return ClusterType.ON_DEMAND
                    return ClusterType.SPOT

        self._committed_region = None
        self._commit_until = step

        if slack <= 0.0:
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        next_step = int(self._next_any_spot[step])
        if next_step >= self._steps:
            return ClusterType.ON_DEMAND

        if slack > self._idle_slack_min:
            return _CT_NONE

        return ClusterType.ON_DEMAND