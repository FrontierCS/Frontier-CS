import json
import math
import os
from argparse import Namespace
from typing import Any, List, Optional, Sequence, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _ct(name: str):
    return getattr(ClusterType, name, None)


CT_SPOT = _ct("SPOT")
CT_OD = _ct("ON_DEMAND")
CT_NONE = _ct("NONE") or _ct("None")


def _is_truthy_token(tok: str) -> Optional[bool]:
    t = tok.strip().lower()
    if not t:
        return None
    if t in ("true", "t", "yes", "y"):
        return True
    if t in ("false", "f", "no", "n"):
        return False
    try:
        v = float(t)
        return v > 0.0
    except Exception:
        return None


def _flatten_json_values(obj: Any) -> List[Any]:
    out: List[Any] = []
    if isinstance(obj, list):
        for x in obj:
            out.extend(_flatten_json_values(x))
    else:
        out.append(obj)
    return out


def _parse_trace_file(path: str) -> List[int]:
    try:
        with open(path, "r") as f:
            first = f.read(4096)
    except Exception:
        return []
    s = first.lstrip()
    if s.startswith("{") or s.startswith("["):
        try:
            obj = json.loads(first + open(path, "r").read())
        except Exception:
            try:
                with open(path, "r") as f:
                    obj = json.load(f)
            except Exception:
                obj = None
        vals: List[int] = []
        if isinstance(obj, dict):
            cand_keys = (
                "availability",
                "avail",
                "spot",
                "has_spot",
                "interruptions",
                "data",
                "trace",
                "series",
                "values",
            )
            arr = None
            for k in cand_keys:
                if k in obj and isinstance(obj[k], (list, tuple)):
                    arr = obj[k]
                    break
            if arr is None:
                for v in obj.values():
                    if isinstance(v, (list, tuple)):
                        arr = v
                        break
            if arr is None:
                return []
            obj = arr

        if isinstance(obj, (list, tuple)):
            # list of dicts or scalars
            if len(obj) == 0:
                return []
            if isinstance(obj[0], dict):
                key_order = ("has_spot", "available", "availability", "spot", "avail")
                for item in obj:
                    if not isinstance(item, dict):
                        continue
                    got = None
                    for k in key_order:
                        if k in item:
                            got = item[k]
                            break
                    if got is None:
                        continue
                    if isinstance(got, bool):
                        vals.append(1 if got else 0)
                    else:
                        try:
                            vals.append(1 if float(got) > 0.0 else 0)
                        except Exception:
                            pass
            else:
                flat = _flatten_json_values(obj)
                for x in flat:
                    if isinstance(x, bool):
                        vals.append(1 if x else 0)
                    else:
                        try:
                            vals.append(1 if float(x) > 0.0 else 0)
                        except Exception:
                            pass
        return vals

    # CSV/TSV/text
    vals: List[int] = []
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p for p in line.replace("\t", ",").split(",") if p.strip() != ""]
                if len(parts) == 0:
                    parts = line.split()
                if not parts:
                    continue
                b = None
                # try from end (often last column is availability)
                for tok in reversed(parts):
                    b = _is_truthy_token(tok)
                    if b is not None:
                        break
                if b is None:
                    continue
                vals.append(1 if b else 0)
    except Exception:
        return []
    return vals


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_mr_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        self._config = config
        self._trace_files = list(config.get("trace_files", []))
        self._raw_traces: List[List[int]] = []
        for p in self._trace_files:
            self._raw_traces.append(_parse_trace_file(p))

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Runtime caches
        self._initialized = False
        self._N = 0
        self._gap = 0.0
        self._avail: List[List[bool]] = []
        self._runlen: List[List[int]] = []
        self._any_spot: List[bool] = []
        self._best_region: List[int] = []
        self._best_run: List[int] = []
        self._next_any: List[int] = []

        self._committed_od = False
        self._work_done = 0.0
        self._td_idx = 0

        return self

    def _get_task_duration_seconds(self) -> float:
        td = getattr(self, "task_duration", None)
        if td is not None:
            return float(td)
        tds = getattr(self, "task_durations", None)
        if tds and len(tds) > 0:
            return float(tds[0])
        return float(getattr(self, "_task_duration", 0.0))

    def _get_deadline_seconds(self) -> float:
        dl = getattr(self, "deadline", None)
        if dl is not None:
            return float(dl)
        return float(getattr(self, "_deadline", 0.0))

    def _get_restart_overhead_seconds(self) -> float:
        ro = getattr(self, "restart_overhead", None)
        if ro is not None:
            return float(ro)
        ros = getattr(self, "restart_overheads", None)
        if ros and len(ros) > 0:
            return float(ros[0])
        return float(getattr(self, "_restart_overhead", 0.0))

    def _ensure_initialized(self):
        if self._initialized:
            return
        self._gap = float(getattr(self.env, "gap_seconds", 1.0))
        deadline = self._get_deadline_seconds()
        if self._gap <= 0:
            self._gap = 1.0
        self._N = int(math.ceil(deadline / self._gap)) if deadline > 0 else 0

        num_regions = int(self.env.get_num_regions())
        raw = self._raw_traces if self._raw_traces else [[] for _ in range(num_regions)]
        if len(raw) < num_regions:
            raw = raw + [[] for _ in range(num_regions - len(raw))]
        elif len(raw) > num_regions:
            raw = raw[:num_regions]

        self._avail = [[False] * self._N for _ in range(num_regions)]
        for r in range(num_regions):
            arr = raw[r] if r < len(raw) else []
            L = len(arr)
            if self._N == 0:
                continue
            if L == 0:
                continue
            if L == self._N:
                self._avail[r] = [bool(x) for x in arr[: self._N]]
            else:
                # Resample to N
                out = self._avail[r]
                # map t -> floor(t*L/N)
                for t in range(self._N):
                    idx = (t * L) // self._N
                    if idx >= L:
                        idx = L - 1
                    out[t] = bool(arr[idx])

        # run lengths
        self._runlen = [[0] * (self._N + 1) for _ in range(num_regions)]
        for r in range(num_regions):
            rl = self._runlen[r]
            av = self._avail[r]
            for t in range(self._N - 1, -1, -1):
                rl[t] = rl[t + 1] + 1 if av[t] else 0

        self._any_spot = [False] * self._N
        self._best_region = [0] * self._N
        self._best_run = [0] * self._N
        for t in range(self._N):
            br = 0
            bv = self._runlen[0][t] if num_regions > 0 else 0
            for r in range(1, num_regions):
                v = self._runlen[r][t]
                if v > bv:
                    bv = v
                    br = r
            self._best_region[t] = br
            self._best_run[t] = bv
            self._any_spot[t] = bv > 0

        self._next_any = [self._N] * (self._N + 1)
        self._next_any[self._N] = self._N
        for t in range(self._N - 1, -1, -1):
            self._next_any[t] = t if self._any_spot[t] else self._next_any[t + 1]

        self._initialized = True

    def _update_work_done(self):
        td = getattr(self, "task_done_time", None)
        if not isinstance(td, list):
            return
        n = len(td)
        if self._td_idx < n:
            s = 0.0
            for i in range(self._td_idx, n):
                try:
                    s += float(td[i])
                except Exception:
                    pass
            self._work_done += s
            self._td_idx = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_initialized()
        self._update_work_done()

        gap = self._gap
        task_duration = self._get_task_duration_seconds()
        deadline = self._get_deadline_seconds()
        restart_overhead = self._get_restart_overhead_seconds()

        if task_duration <= 0 or deadline <= 0:
            return CT_NONE

        remaining_work = task_duration - self._work_done
        if remaining_work <= 1e-9:
            return CT_NONE

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        remaining_time = deadline - elapsed
        if remaining_time <= 0:
            return CT_NONE

        if self._committed_od:
            return CT_OD

        t = int(elapsed // gap) if gap > 0 else 0
        if t < 0:
            t = 0
        if t >= self._N:
            # Past our precomputed horizon; be safe and use on-demand
            self._committed_od = True
            return CT_OD

        # Helpers
        def can_idle_one_step() -> bool:
            rt = remaining_time - gap
            if rt < 0:
                return False
            # If we idle, assume we will need to restart on-demand next step
            return rt + 1e-9 >= remaining_work + restart_overhead

        # If overhead pending, avoid switching because it can reset overhead.
        rem_ov = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        overhead_pending = rem_ov > 1e-9

        current_region = int(self.env.get_current_region())

        # Always take spot if it's available in current region (no region switch needed).
        if has_spot:
            return CT_SPOT

        # No spot in current region now.
        any_spot_now = self._any_spot[t]
        if overhead_pending:
            # Prefer waiting to pay overhead on spot later; only go on-demand if we cannot afford to idle.
            if can_idle_one_step():
                return CT_NONE
            self._committed_od = True
            return CT_OD

        # overhead not pending
        if any_spot_now:
            br = self._best_region[t]
            run = self._best_run[t]
            # Only switch if net progress can be positive (run*gap > overhead)
            if run > 0 and (run * gap) > (restart_overhead + 1e-9):
                if br != current_region:
                    try:
                        self.env.switch_region(br)
                    except Exception:
                        pass
                return CT_SPOT

        # No good spot option now; idle if safe, else commit to on-demand
        if can_idle_one_step():
            return CT_NONE

        self._committed_od = True
        return CT_OD