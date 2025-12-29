import json
import math
import os
import csv
import pickle
from array import array
from argparse import Namespace
from typing import Any, List, Optional, Sequence, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


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

        self._trace_files: List[str] = list(config.get("trace_files", [])) if isinstance(config, dict) else []
        self._raw_traces: List[Optional[List[bool]]] = []
        for p in self._trace_files:
            self._raw_traces.append(self._load_trace_file(p))

        self._runtime_inited = False
        self._trace_trusted = any(t is not None and len(t) > 0 for t in self._raw_traces)
        self._trace_disabled = not self._trace_trusted

        self._avail: List[Optional[bytearray]] = []
        self._runlen: List[Optional[array]] = []
        self._any_avail: Optional[bytearray] = None

        self._done_len = 0
        self._done_work = 0.0
        self._committed_on_demand = False

        return self

    @staticmethod
    def _to_bool(x: Any) -> Optional[bool]:
        if x is None:
            return None
        if isinstance(x, bool):
            return x
        if isinstance(x, (int, float)):
            return bool(x > 0)
        s = str(x).strip().lower()
        if s in ("1", "true", "t", "yes", "y"):
            return True
        if s in ("0", "false", "f", "no", "n"):
            return False
        try:
            return float(s) > 0
        except Exception:
            return None

    def _load_trace_file(self, path: str) -> Optional[List[bool]]:
        if not path or not isinstance(path, str):
            return None
        if not os.path.exists(path):
            return None
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext in (".pkl", ".pickle"):
                with open(path, "rb") as f:
                    obj = pickle.load(f)
                seq = None
                if isinstance(obj, dict):
                    for v in obj.values():
                        if isinstance(v, (list, tuple)):
                            seq = v
                            break
                elif isinstance(obj, (list, tuple)):
                    seq = obj
                if seq is None:
                    return None
                out: List[bool] = []
                for v in seq:
                    b = self._to_bool(v)
                    if b is not None:
                        out.append(b)
                return out if out else None

            if ext in (".npy", ".npz"):
                try:
                    import numpy as np  # type: ignore
                except Exception:
                    return None
                arr = np.load(path, allow_pickle=True)
                if isinstance(arr, np.lib.npyio.NpzFile):
                    keys = list(arr.keys())
                    if not keys:
                        return None
                    data = arr[keys[0]]
                else:
                    data = arr
                flat = data.reshape(-1).tolist()
                out = []
                for v in flat:
                    b = self._to_bool(v)
                    if b is not None:
                        out.append(b)
                return out if out else None

            if ext == ".json":
                with open(path, "r") as f:
                    obj = json.load(f)
                seq = None
                if isinstance(obj, list):
                    seq = obj
                elif isinstance(obj, dict):
                    for k in ("availability", "avail", "spot", "has_spot", "trace", "data"):
                        if k in obj and isinstance(obj[k], list):
                            seq = obj[k]
                            break
                    if seq is None:
                        for v in obj.values():
                            if isinstance(v, list):
                                seq = v
                                break
                if seq is None:
                    return None
                out = []
                for v in seq:
                    b = self._to_bool(v)
                    if b is not None:
                        out.append(b)
                return out if out else None

            # text/csv fallback
            with open(path, "r", newline="") as f:
                sample = f.read(4096)
                f.seek(0)
                use_csv = ("," in sample) or ("\t" in sample)
                out: List[bool] = []
                if use_csv:
                    reader = csv.reader(f)
                    for row in reader:
                        if not row:
                            continue
                        token = row[-1]
                        b = self._to_bool(token)
                        if b is None:
                            continue
                        out.append(b)
                else:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        parts = line.replace(",", " ").split()
                        if not parts:
                            continue
                        b = self._to_bool(parts[-1])
                        if b is None:
                            continue
                        out.append(b)
                return out if out else None
        except Exception:
            return None

    def _init_runtime(self) -> None:
        if self._runtime_inited:
            return
        self._runtime_inited = True

        self._gap = float(getattr(self.env, "gap_seconds", 3600.0))
        self._deadline = float(getattr(self, "deadline", 0.0))
        self._task_duration = float(getattr(self, "task_duration", 0.0))
        self._restart_overhead = float(getattr(self, "restart_overhead", 0.0))

        self._horizon_steps = int(math.ceil(self._deadline / self._gap)) + 4

        self._avail = []
        self._runlen = []
        self._any_avail = None

        if self._trace_disabled:
            return

        num_regions = int(self.env.get_num_regions())
        raw = list(self._raw_traces) if self._raw_traces else []
        if len(raw) < num_regions:
            raw.extend([None] * (num_regions - len(raw)))
        elif len(raw) > num_regions:
            raw = raw[:num_regions]

        avail_bytes: List[Optional[bytearray]] = []
        runlens: List[Optional[array]] = []

        for r in range(num_regions):
            t = raw[r]
            if not t:
                avail_bytes.append(None)
                runlens.append(None)
                continue

            L = len(t)
            target = self._horizon_steps
            b = bytearray(target)
            if L >= target:
                for i in range(target):
                    b[i] = 1 if t[i] else 0
            else:
                if L == 0:
                    avail_bytes.append(None)
                    runlens.append(None)
                    continue
                for i in range(target):
                    b[i] = 1 if t[i % L] else 0

            rl = array("I", [0]) * (target + 1)
            for i in range(target - 1, -1, -1):
                rl[i] = (rl[i + 1] + 1) if b[i] else 0

            avail_bytes.append(b)
            runlens.append(rl)

        if not any(a is not None for a in avail_bytes):
            self._trace_disabled = True
            return

        any_av = bytearray(self._horizon_steps)
        for i in range(self._horizon_steps):
            v = 0
            for r in range(num_regions):
                ar = avail_bytes[r]
                if ar is not None and ar[i]:
                    v = 1
                    break
            any_av[i] = v

        self._avail = avail_bytes
        self._runlen = runlens
        self._any_avail = any_av

    def _update_done_work(self) -> None:
        td = getattr(self, "task_done_time", None)
        if not isinstance(td, list):
            return
        n = len(td)
        if n <= self._done_len:
            return
        s = 0.0
        for i in range(self._done_len, n):
            try:
                s += float(td[i])
            except Exception:
                pass
        self._done_work += s
        self._done_len = n

    def _step_index(self) -> int:
        gap = self._gap
        t = float(getattr(self.env, "elapsed_seconds", 0.0))
        if gap <= 0:
            return 0
        return int(t / gap + 1e-9)

    def _get_avail_vector(self, idx: int, has_spot: bool) -> Tuple[Optional[List[bool]], Optional[List[int]]]:
        num_regions = int(self.env.get_num_regions())

        if not self._trace_disabled and self._avail and idx < self._horizon_steps:
            cur_r = int(self.env.get_current_region())
            ar = self._avail[cur_r] if 0 <= cur_r < len(self._avail) else None
            if ar is not None:
                trace_has = bool(ar[idx])
                if trace_has != bool(has_spot):
                    self._trace_disabled = True
                    self._committed_on_demand = self._committed_on_demand  # no-op
                else:
                    av: List[bool] = [False] * num_regions
                    rl: List[int] = [0] * num_regions
                    for r in range(num_regions):
                        abr = self._avail[r]
                        if abr is None:
                            continue
                        v = bool(abr[idx])
                        av[r] = v
                        if v:
                            rlr = self._runlen[r]
                            rl[r] = int(rlr[idx]) if rlr is not None else 0
                    return av, rl

        # No trusted trace vector available.
        return None, None

    def _safe_spot_finish_region(
        self,
        idx: int,
        remaining_work: float,
        remaining_time: float,
        last_cluster_type: ClusterType,
        avail_vec: List[bool],
        run_vec: List[int],
    ) -> Optional[int]:
        gap = self._gap
        cur_r = int(self.env.get_current_region())
        best_r = None
        best_extra = -1.0

        for r, ok in enumerate(avail_vec):
            if not ok:
                continue
            run = run_vec[r]
            if run <= 0:
                continue

            if last_cluster_type == ClusterType.SPOT and r == cur_r:
                overhead_start = float(getattr(self, "remaining_restart_overhead", 0.0))
            else:
                overhead_start = self._restart_overhead

            total_time = run * gap
            if total_time > remaining_time + 1e-9:
                run = int(remaining_time // gap)
                total_time = run * gap
                if run <= 0:
                    continue

            max_work = total_time - overhead_start
            if max_work + 1e-9 >= remaining_work:
                extra = max_work - remaining_work
                if extra > best_extra:
                    best_extra = extra
                    best_r = r

        return best_r

    def _best_spot_region(
        self,
        idx: int,
        remaining_work: float,
        last_cluster_type: ClusterType,
        avail_vec: List[bool],
        run_vec: List[int],
        slack: float,
    ) -> Optional[int]:
        gap = self._gap
        cur_r = int(self.env.get_current_region())

        best_r = None
        best_run = -1
        for r, ok in enumerate(avail_vec):
            if not ok:
                continue
            run = run_vec[r]
            if run > best_run:
                best_run = run
                best_r = r

        if best_r is None:
            return None

        if best_r == cur_r:
            return best_r

        cur_run = run_vec[cur_r] if 0 <= cur_r < len(run_vec) and avail_vec[cur_r] else 0

        if last_cluster_type == ClusterType.SPOT and avail_vec[cur_r]:
            lost_work = min(self._restart_overhead, gap)
            gain_work = max(0.0, (best_run - cur_run) * gap)
            if gain_work <= lost_work + 1e-9:
                return cur_r

        # If very close to finishing, avoid a switch unless necessary.
        if remaining_work <= gap and avail_vec[cur_r]:
            return cur_r

        return best_r

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_runtime()
        self._update_done_work()

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        remaining_time = self._deadline - elapsed
        remaining_work = self._task_duration - self._done_work

        if remaining_work <= 0.0:
            return ClusterType.NONE

        if remaining_time <= 0.0:
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        slack = remaining_time - remaining_work
        threshold_slack = max(2.0 * self._gap, 5.0 * self._restart_overhead)

        if self._committed_on_demand:
            return ClusterType.ON_DEMAND

        idx = self._step_index()

        avail_vec, run_vec = self._get_avail_vector(idx, has_spot)

        if slack <= threshold_slack:
            if avail_vec is not None and run_vec is not None:
                safe_r = self._safe_spot_finish_region(
                    idx=idx,
                    remaining_work=remaining_work,
                    remaining_time=remaining_time,
                    last_cluster_type=last_cluster_type,
                    avail_vec=avail_vec,
                    run_vec=run_vec,
                )
                if safe_r is not None:
                    cur_r = int(self.env.get_current_region())
                    if safe_r != cur_r:
                        self.env.switch_region(safe_r)
                    return ClusterType.SPOT
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        if avail_vec is not None and run_vec is not None:
            if any(avail_vec):
                best_r = self._best_spot_region(
                    idx=idx,
                    remaining_work=remaining_work,
                    last_cluster_type=last_cluster_type,
                    avail_vec=avail_vec,
                    run_vec=run_vec,
                    slack=slack,
                )
                if best_r is not None:
                    cur_r = int(self.env.get_current_region())
                    if best_r != cur_r:
                        self.env.switch_region(best_r)
                    return ClusterType.SPOT

            return ClusterType.NONE

        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE