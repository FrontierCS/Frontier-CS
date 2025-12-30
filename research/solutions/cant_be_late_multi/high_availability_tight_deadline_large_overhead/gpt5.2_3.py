import json
import math
import os
from argparse import Namespace
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _to_bool(x: Any) -> bool:
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return x > 0.5
    if x is None:
        return False
    s = str(x).strip().lower()
    if s in ("1", "true", "t", "yes", "y", "available", "avail"):
        return True
    if s in ("0", "false", "f", "no", "n", "unavailable", "unavail", ""):
        return False
    try:
        return float(s) > 0.5
    except Exception:
        return False


def _ceil_div_float(a: float, b: float) -> int:
    if b <= 0:
        return 0
    if a <= 0:
        return 0
    # Small epsilon to avoid rounding issues when a/b is very close to an int.
    return int(math.ceil((a / b) - 1e-12))


def _parse_trace_obj(obj: Any) -> Optional[List[bool]]:
    if obj is None:
        return None

    if isinstance(obj, list):
        if not obj:
            return []
        if isinstance(obj[0], dict):
            keys = ("available", "availability", "has_spot", "spot", "is_available", "capacity")
            for k in keys:
                if k in obj[0]:
                    return [_to_bool(it.get(k)) for it in obj]
            # fallback: any numeric/bool field in dict
            out: List[bool] = []
            for it in obj:
                v = None
                for vv in it.values():
                    if isinstance(vv, (bool, int, float, str)) and str(vv).strip() != "":
                        v = vv
                        break
                out.append(_to_bool(v))
            return out
        return [_to_bool(v) for v in obj]

    if isinstance(obj, dict):
        candidates = (
            "availability",
            "available",
            "has_spot",
            "spot",
            "trace",
            "values",
            "data",
            "series",
            "timeline",
        )
        for k in candidates:
            if k in obj:
                parsed = _parse_trace_obj(obj[k])
                if parsed is not None:
                    return parsed
        # if dict values contain one big list
        for v in obj.values():
            parsed = _parse_trace_obj(v)
            if isinstance(parsed, list):
                return parsed

    return None


def _load_trace_file(path: str) -> Optional[List[bool]]:
    if not path:
        return None
    try:
        with open(path, "rb") as f:
            data = f.read()
    except Exception:
        return None

    # Try JSON
    try:
        obj = json.loads(data.decode("utf-8"))
        parsed = _parse_trace_obj(obj)
        if parsed is not None:
            return parsed
    except Exception:
        pass

    # Try text tokens
    try:
        text = data.decode("utf-8", errors="ignore")
        out: List[bool] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                continue
            parts = [p for p in line.replace(",", " ").split() if p]
            if not parts:
                continue
            # Heuristic: if there's a timestamp + value, take last token.
            out.append(_to_bool(parts[-1]))
        if out:
            return out
    except Exception:
        pass

    return None


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_region_aware_v1"

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

        self._forced_on_demand = False

        self._done_sum = 0.0
        self._done_len = 0

        self._trace_loaded = False
        self._spot_trace: List[List[bool]] = []
        self._spot_run: List[List[int]] = []
        self._spot_next: List[List[int]] = []

        self._trace_files: List[str] = []
        if isinstance(config, dict) and "trace_files" in config and isinstance(config["trace_files"], list):
            self._trace_files = [str(p) for p in config["trace_files"]]

        self._init_traces()

        return self

    def _init_traces(self) -> None:
        try:
            gap = float(self.env.gap_seconds)
            if gap <= 0:
                return
            horizon_steps = int(math.ceil(float(self.deadline) / gap)) + 5
            num_regions = int(self.env.get_num_regions())
            if num_regions <= 0:
                return

            if not self._trace_files:
                return

            traces: List[List[bool]] = []
            for i in range(num_regions):
                path = self._trace_files[i] if i < len(self._trace_files) else ""
                tr = _load_trace_file(path)
                if tr is None:
                    traces.append([False] * horizon_steps)
                    continue
                if len(tr) >= horizon_steps:
                    traces.append(tr[:horizon_steps])
                else:
                    pad_val = tr[-1] if tr else False
                    traces.append(tr + [pad_val] * (horizon_steps - len(tr)))

            spot_run: List[List[int]] = []
            spot_next: List[List[int]] = []
            INF = 10**12
            for r in range(num_regions):
                tr = traces[r]
                L = len(tr)
                run = [0] * L
                nxt = [INF] * L
                rr = 0
                nn = INF
                for t in range(L - 1, -1, -1):
                    if tr[t]:
                        rr += 1
                        nn = t
                    else:
                        rr = 0
                    run[t] = rr
                    nxt[t] = nn
                spot_run.append(run)
                spot_next.append(nxt)

            self._spot_trace = traces
            self._spot_run = spot_run
            self._spot_next = spot_next
            self._trace_loaded = True
        except Exception:
            self._trace_loaded = False
            self._spot_trace = []
            self._spot_run = []
            self._spot_next = []

    def _update_done_sum(self) -> None:
        td = self.task_done_time
        n = len(td)
        if n <= self._done_len:
            return
        # Usually one element per step; handle bursts.
        self._done_sum += sum(td[self._done_len : n])
        self._done_len = n

    def _spot_pred(self, region: int, step_idx: int) -> bool:
        if not self._trace_loaded:
            return False
        if region < 0 or region >= len(self._spot_trace):
            return False
        tr = self._spot_trace[region]
        if step_idx < 0:
            return False
        if step_idx >= len(tr):
            return tr[-1] if tr else False
        return bool(tr[step_idx])

    def _run_pred(self, region: int, step_idx: int) -> int:
        if not self._trace_loaded:
            return 0
        if region < 0 or region >= len(self._spot_run):
            return 0
        run = self._spot_run[region]
        if step_idx < 0:
            return 0
        if step_idx >= len(run):
            return 0
        return int(run[step_idx])

    def _next_pred(self, region: int, step_idx: int) -> int:
        if not self._trace_loaded:
            return 10**12
        if region < 0 or region >= len(self._spot_next):
            return 10**12
        nxt = self._spot_next[region]
        if step_idx < 0:
            return 10**12
        if step_idx >= len(nxt):
            return 10**12
        return int(nxt[step_idx])

    def _best_region_for_step(self, step_idx: int) -> Optional[int]:
        try:
            num_regions = int(self.env.get_num_regions())
        except Exception:
            return None
        if num_regions <= 0 or not self._trace_loaded:
            return None

        best_r = -1
        best_run = -1
        for r in range(num_regions):
            if self._spot_pred(r, step_idx):
                run = self._run_pred(r, step_idx)
                if run > best_run:
                    best_run = run
                    best_r = r
        if best_r != -1:
            return best_r

        # No region has spot at this step; pick region with earliest next spot.
        best_r = 0
        best_nxt = 10**12
        for r in range(num_regions):
            nxt = self._next_pred(r, step_idx)
            if nxt < best_nxt:
                best_nxt = nxt
                best_r = r
        return best_r

    def _time_needed_if_run_forever(self, remaining_work: float, initial_overhead: float) -> float:
        gap = float(self.env.gap_seconds)
        if remaining_work <= 0:
            return 0.0
        steps = _ceil_div_float(remaining_work + max(0.0, initial_overhead), gap)
        return steps * gap

    def _work_done_one_step(self, cluster: ClusterType, last_cluster_type: ClusterType) -> float:
        gap = float(self.env.gap_seconds)
        if cluster == ClusterType.NONE:
            return 0.0
        if last_cluster_type == cluster:
            ro = float(self.remaining_restart_overhead)
        else:
            ro = float(self.restart_overhead)
        return max(0.0, gap - max(0.0, ro))

    def _safe_to_use_spot_this_step(self, remaining_work: float, remaining_time: float, last_cluster_type: ClusterType) -> bool:
        gap = float(self.env.gap_seconds)
        if remaining_time < gap:
            return False
        work_done = self._work_done_one_step(ClusterType.SPOT, last_cluster_type)
        w_after = max(0.0, remaining_work - work_done)
        t_after = remaining_time - gap
        if w_after <= 0:
            return True
        # If we switch to on-demand next step, assume full restart overhead applies.
        t_need = self._time_needed_if_run_forever(w_after, float(self.restart_overhead))
        return t_after >= t_need

    def _safe_to_wait_one_step(self, remaining_work: float, remaining_time: float) -> bool:
        gap = float(self.env.gap_seconds)
        if remaining_time < gap:
            return False
        t_after = remaining_time - gap
        t_need = self._time_needed_if_run_forever(remaining_work, float(self.restart_overhead))
        return t_after >= t_need

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_done_sum()

        gap = float(self.env.gap_seconds)
        elapsed = float(self.env.elapsed_seconds)
        remaining_time = float(self.deadline) - elapsed
        remaining_work = float(self.task_duration) - float(self._done_sum)

        if remaining_work <= 0.0 or remaining_time <= 0.0:
            return ClusterType.NONE

        # Compute feasibility if we go on-demand from now until finish.
        if last_cluster_type == ClusterType.ON_DEMAND:
            od_initial_overhead = float(self.remaining_restart_overhead)
        else:
            od_initial_overhead = float(self.restart_overhead)
        time_need_od_now = self._time_needed_if_run_forever(remaining_work, od_initial_overhead)
        if remaining_time < time_need_od_now:
            self._forced_on_demand = True

        if self._forced_on_demand:
            return ClusterType.ON_DEMAND

        # Decide cluster action.
        action: ClusterType
        if has_spot:
            safe_spot = self._safe_to_use_spot_this_step(remaining_work, remaining_time, last_cluster_type)

            if last_cluster_type == ClusterType.ON_DEMAND:
                # Avoid thrashing when overhead spans many steps: only switch back if spot looks stable or we have no trace.
                min_run_steps = max(1, int(math.ceil((2.0 * float(self.restart_overhead)) / max(gap, 1e-9))))
                if self._trace_loaded:
                    cur_region = int(self.env.get_current_region())
                    step_idx = int(elapsed // gap) if gap > 0 else 0
                    pred_run = self._run_pred(cur_region, step_idx)
                    if pred_run < min_run_steps:
                        action = ClusterType.ON_DEMAND
                    else:
                        action = ClusterType.SPOT if safe_spot else ClusterType.ON_DEMAND
                else:
                    action = ClusterType.SPOT if safe_spot else ClusterType.ON_DEMAND
            else:
                action = ClusterType.SPOT if safe_spot else ClusterType.ON_DEMAND
        else:
            # No spot: prefer waiting (free) if it won't jeopardize ability to finish using on-demand later.
            if last_cluster_type == ClusterType.ON_DEMAND:
                action = ClusterType.ON_DEMAND
            else:
                action = ClusterType.NONE if self._safe_to_wait_one_step(remaining_work, remaining_time) else ClusterType.ON_DEMAND

        # Region selection (conservative): switch only when we are not actively running SPOT,
        # and avoid switching while on-demand to reduce risk if region-switch incurs restart in some environments.
        if self._trace_loaded and action != ClusterType.SPOT and last_cluster_type != ClusterType.ON_DEMAND:
            try:
                cur_region = int(self.env.get_current_region())
                step_idx = int(elapsed // gap) if gap > 0 else 0
                target = self._best_region_for_step(step_idx + 1)
                if target is not None and target != cur_region:
                    self.env.switch_region(int(target))
            except Exception:
                pass

        return action