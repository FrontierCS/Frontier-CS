import json
from argparse import Namespace
from array import array
from math import sqrt, log
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None


def _as_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _normalize_availability_seq(seq: Sequence[Any]) -> bytearray:
    out = bytearray()
    append = out.append
    for v in seq:
        if isinstance(v, bool):
            append(1 if v else 0)
        elif isinstance(v, (int, float)):
            append(1 if float(v) > 0.0 else 0)
        elif isinstance(v, str):
            s = v.strip().lower()
            if s in ("1", "true", "t", "yes", "y", "spot", "available", "avail"):
                append(1)
            else:
                try:
                    append(1 if float(s) > 0.0 else 0)
                except Exception:
                    append(0)
        elif isinstance(v, dict):
            val = None
            for k in ("has_spot", "spot", "availability", "available", "avail", "value", "v"):
                if k in v:
                    val = v[k]
                    break
            append(1 if _as_float(val, 0.0) > 0.0 else 0)
        else:
            append(0)
    return out


def _extract_seq_from_json(obj: Any) -> Optional[Sequence[Any]]:
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in ("availability", "avail", "available", "spot", "has_spot", "values", "data", "trace", "series"):
            v = obj.get(k)
            if isinstance(v, list):
                return v
        for v in obj.values():
            if isinstance(v, list) and v:
                if all(isinstance(x, (int, float, bool, str, dict)) for x in v[: min(10, len(v))]):
                    return v
    return None


def _load_availability_file(path: str) -> Optional[bytearray]:
    if not path:
        return None
    p = path.lower()

    if np is not None and (p.endswith(".npy") or p.endswith(".npz")):
        try:
            if p.endswith(".npz"):
                data = np.load(path)
                key = None
                for k in data.files:
                    key = k
                    break
                if key is None:
                    return None
                arr = data[key]
            else:
                arr = np.load(path, allow_pickle=True)
            if hasattr(arr, "tolist"):
                arr_list = arr.tolist()
                if isinstance(arr_list, list):
                    return _normalize_availability_seq(arr_list)
        except Exception:
            pass

    try:
        with open(path, "rb") as f:
            raw = f.read()
    except Exception:
        return None

    if not raw:
        return None

    try:
        s = raw.decode("utf-8", errors="ignore").strip()
    except Exception:
        return None

    if not s:
        return None

    if s[0] in "[{":
        try:
            obj = json.loads(s)
            seq = _extract_seq_from_json(obj)
            if seq is None:
                return None
            return _normalize_availability_seq(seq)
        except Exception:
            pass

    lines = s.splitlines()
    vals: List[int] = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [x.strip() for x in line.replace("\t", " ").split(",") if x.strip()]
        if len(parts) <= 1:
            parts = [x for x in line.replace("\t", " ").split(" ") if x]
        if not parts:
            continue
        token = parts[-1]
        token_l = token.lower()
        if token_l in ("true", "t", "yes", "y", "spot", "available", "avail"):
            vals.append(1)
            continue
        if token_l in ("false", "f", "no", "n", "none", "unavailable"):
            vals.append(0)
            continue
        try:
            vals.append(1 if float(token) > 0.0 else 0)
        except Exception:
            vals.append(0)

    if not vals:
        return None
    return bytearray(vals)


def _precompute_run_and_next_true(avail: bytearray) -> Tuple[array, array]:
    n = len(avail)
    run = array("I", [0]) * (n + 1)
    inf = n + 1
    nxt = array("I", [inf]) * (n + 2)
    nxt[n] = inf
    nxt[n + 1] = inf
    for i in range(n - 1, -1, -1):
        if avail[i]:
            run[i] = run[i + 1] + 1
            nxt[i] = i
        else:
            run[i] = 0
            nxt[i] = nxt[i + 1]
    return run, nxt


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v1"

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

        self._trace_files = list(config.get("trace_files", [])) if isinstance(config.get("trace_files", []), list) else []
        self._lazy_inited = False

        self._forced_on_demand = False

        self._done_sum = 0.0
        self._done_len = 0

        self._timestep = 0
        self._last_region_switch_step = -10**18
        self._dwell_steps = 1

        self._n_regions = 0
        self._spot_seen = []
        self._total_seen = []

        self._trace_avail: Optional[List[Optional[bytearray]]] = None
        self._trace_run: Optional[List[Optional[array]]] = None
        self._trace_next_true: Optional[List[Optional[array]]] = None
        self._trace_horizon = 0

        return self

    def _lazy_init(self) -> None:
        if self._lazy_inited:
            return
        self._lazy_inited = True

        try:
            self._n_regions = int(self.env.get_num_regions())
        except Exception:
            self._n_regions = len(self._trace_files) if self._trace_files else 1

        self._spot_seen = [0] * self._n_regions
        self._total_seen = [0] * self._n_regions

        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        dwell_seconds = 600.0
        self._dwell_steps = max(1, int(dwell_seconds / gap))

        deadline = self._get_deadline_seconds()
        self._trace_horizon = max(1, int(deadline / gap) + 5)

        if self._trace_files and len(self._trace_files) >= self._n_regions:
            avs: List[Optional[bytearray]] = [None] * self._n_regions
            runs: List[Optional[array]] = [None] * self._n_regions
            nxts: List[Optional[array]] = [None] * self._n_regions
            for i in range(self._n_regions):
                avail = _load_availability_file(self._trace_files[i])
                if avail is None:
                    continue
                if len(avail) > self._trace_horizon:
                    avail = avail[: self._trace_horizon]
                elif len(avail) < self._trace_horizon:
                    avail = avail + bytearray(self._trace_horizon - len(avail))
                avs[i] = avail
                run, nxt = _precompute_run_and_next_true(avail)
                runs[i] = run
                nxts[i] = nxt
            if any(a is not None for a in avs):
                self._trace_avail = avs
                self._trace_run = runs
                self._trace_next_true = nxts

    def _get_task_duration_seconds(self) -> float:
        td = getattr(self, "task_duration", 0.0)
        if isinstance(td, (list, tuple)):
            return float(td[0]) if td else 0.0
        return float(td)

    def _get_deadline_seconds(self) -> float:
        dl = getattr(self, "deadline", 0.0)
        if isinstance(dl, (list, tuple)):
            return float(dl[0]) if dl else 0.0
        return float(dl)

    def _get_restart_overhead_seconds(self) -> float:
        ro = getattr(self, "restart_overhead", 0.0)
        if isinstance(ro, (list, tuple)):
            return float(ro[0]) if ro else 0.0
        return float(ro)

    def _get_remaining_restart_overhead_seconds(self) -> float:
        r = getattr(self, "remaining_restart_overhead", 0.0)
        if isinstance(r, (list, tuple)):
            return float(r[0]) if r else 0.0
        return float(r)

    def _update_done_sum(self) -> None:
        tdt = getattr(self, "task_done_time", [])
        if not isinstance(tdt, list):
            return
        n = len(tdt)
        if n > self._done_len:
            self._done_sum += float(sum(tdt[self._done_len : n]))
            self._done_len = n

    def _choose_region_for_next_step(self, next_step_idx: int) -> int:
        cur = int(self.env.get_current_region())
        if self._trace_avail is not None and self._trace_run is not None and self._trace_next_true is not None:
            best = -1
            best_run = -1
            for r in range(self._n_regions):
                avail = self._trace_avail[r]
                run = self._trace_run[r]
                if avail is None or run is None:
                    continue
                if 0 <= next_step_idx < len(avail) and avail[next_step_idx]:
                    rl = int(run[next_step_idx])
                    if rl > best_run:
                        best_run = rl
                        best = r
            if best != -1:
                return best

            best = -1
            best_nt = 1 << 60
            for r in range(self._n_regions):
                nxt = self._trace_next_true[r]
                if nxt is None:
                    continue
                if 0 <= next_step_idx < len(nxt):
                    nt = int(nxt[next_step_idx])
                else:
                    nt = 1 << 60
                if nt < best_nt:
                    best_nt = nt
                    best = r
            if best != -1:
                return best
            return cur

        t = self._timestep + 1
        ln = log(max(2.0, float(t)))
        best = cur
        best_ucb = -1e18
        for r in range(self._n_regions):
            n = self._total_seen[r]
            s = self._spot_seen[r]
            mean = (s + 1.0) / (n + 2.0)
            bonus = sqrt(2.0 * ln / (n + 1.0))
            ucb = mean + bonus
            if ucb > best_ucb:
                best_ucb = ucb
                best = r
        return best

    def _maybe_switch_region(self, target: int) -> None:
        if target < 0 or target >= self._n_regions:
            return
        cur = int(self.env.get_current_region())
        if target == cur:
            return
        if (self._timestep - self._last_region_switch_step) < self._dwell_steps:
            return
        try:
            self.env.switch_region(int(target))
            self._last_region_switch_step = self._timestep
        except Exception:
            pass

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._timestep += 1

        cur_region = int(self.env.get_current_region())
        if 0 <= cur_region < self._n_regions:
            self._total_seen[cur_region] += 1
            if has_spot:
                self._spot_seen[cur_region] += 1

        self._update_done_sum()

        task_duration = self._get_task_duration_seconds()
        deadline = self._get_deadline_seconds()
        restart_overhead = self._get_restart_overhead_seconds()
        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        remaining_work = max(0.0, task_duration - self._done_sum)
        time_left = max(0.0, deadline - elapsed)

        if remaining_work <= 1e-9:
            return ClusterType.NONE

        if self._forced_on_demand:
            return ClusterType.ON_DEMAND

        remaining_ro = self._get_remaining_restart_overhead_seconds()
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_needed = max(0.0, remaining_ro)
        else:
            overhead_needed = max(0.0, restart_overhead)

        commit_margin = 2.0 * gap + restart_overhead
        if time_left <= (remaining_work + overhead_needed + commit_margin):
            self._forced_on_demand = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        step_idx = int(elapsed / gap + 1e-9)
        target_region = self._choose_region_for_next_step(step_idx + 1)
        self._maybe_switch_region(target_region)

        return ClusterType.NONE