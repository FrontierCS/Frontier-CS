import json
from argparse import Namespace
from array import array
from typing import Any, Dict, List, Optional, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


_CT_NONE = getattr(ClusterType, "NONE", getattr(ClusterType, "None", None))


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_wait_for_spot_v1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._have_traces: bool = False
        self._spot: List[bytearray] = []
        self._run_len: List[array] = []
        self._next_spot: List[array] = []
        self._best_region_at: Optional[array] = None
        self._next_any_spot: Optional[array] = None
        self._n_steps: int = 0
        self._inf_idx: int = 0

        self._initialized: bool = False
        self._gap: float = 0.0
        self._min_switch_interval_steps: int = 1
        self._finish_buffer: float = 0.0
        self._pause_buffer: float = 0.0

        self._last_switch_step: int = -10**18
        self._committed_on_demand: bool = False

        self._work_done: float = 0.0
        self._task_done_len: int = 0

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

        trace_files = config.get("trace_files", None)
        if trace_files:
            try:
                self._load_and_precompute_traces(trace_files)
            except Exception:
                self._have_traces = False
                self._spot = []
                self._run_len = []
                self._next_spot = []
                self._best_region_at = None
                self._next_any_spot = None
                self._n_steps = 0
                self._inf_idx = 0

        return self

    @staticmethod
    def _parse_avail_token(tok: str) -> Optional[int]:
        t = tok.strip().strip('"').strip("'").lower()
        if not t:
            return None
        if t in ("1", "true", "t", "yes", "y"):
            return 1
        if t in ("0", "false", "f", "no", "n"):
            return 0
        try:
            return 1 if float(t) > 0.0 else 0
        except Exception:
            return None

    def _read_trace_file(self, path: str) -> bytearray:
        if path.lower().endswith(".json"):
            with open(path, "r") as f:
                obj = json.load(f)
            data = None
            if isinstance(obj, list):
                data = obj
            elif isinstance(obj, dict):
                for k in ("spot", "availability", "avail", "has_spot", "data", "trace"):
                    if k in obj and isinstance(obj[k], list):
                        data = obj[k]
                        break
                if data is None:
                    for v in obj.values():
                        if isinstance(v, list):
                            data = v
                            break
            if data is None:
                return bytearray()
            out = bytearray()
            for x in data:
                if isinstance(x, bool):
                    out.append(1 if x else 0)
                elif isinstance(x, (int, float)):
                    out.append(1 if float(x) > 0.0 else 0)
                elif isinstance(x, str):
                    v = self._parse_avail_token(x)
                    if v is None:
                        continue
                    out.append(v)
                else:
                    continue
            return out

        out = bytearray()
        with open(path, "r") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                parts = s.replace(",", " ").split()
                if not parts:
                    continue
                v = self._parse_avail_token(parts[-1])
                if v is None:
                    continue
                out.append(v)
        return out

    def _load_and_precompute_traces(self, trace_files: List[str]) -> None:
        spot = []
        max_len = 0
        for p in trace_files:
            arr = self._read_trace_file(p)
            spot.append(arr)
            if len(arr) > max_len:
                max_len = len(arr)

        if max_len <= 0 or not spot:
            self._have_traces = False
            return

        self._n_steps = max_len
        self._inf_idx = self._n_steps + 5

        padded_spot: List[bytearray] = []
        for arr in spot:
            if len(arr) < self._n_steps:
                a = bytearray(arr)
                a.extend(b"\x00" * (self._n_steps - len(a)))
                padded_spot.append(a)
            else:
                padded_spot.append(arr[: self._n_steps])

        self._spot = padded_spot
        self._have_traces = True

        num_regions = len(self._spot)
        self._run_len = []
        self._next_spot = []

        for r in range(num_regions):
            a = self._spot[r]
            run = array("I", [0]) * (self._n_steps + 1)
            nxt = array("I", [self._inf_idx]) * (self._n_steps + 1)
            next_idx = self._inf_idx
            for i in range(self._n_steps - 1, -1, -1):
                if a[i]:
                    run[i] = run[i + 1] + 1
                    next_idx = i
                else:
                    run[i] = 0
                nxt[i] = next_idx
            self._run_len.append(run)
            self._next_spot.append(nxt)

        best_region_at = array("B", [255]) * (self._n_steps + 1)
        next_any = array("I", [self._inf_idx]) * (self._n_steps + 1)

        for i in range(self._n_steps - 1, -1, -1):
            best_r = 255
            best_run = 0
            min_next = self._inf_idx
            for r in range(num_regions):
                nr = self._next_spot[r][i]
                if nr < min_next:
                    min_next = nr
                rl = self._run_len[r][i]
                if rl > best_run:
                    best_run = rl
                    best_r = r
            best_region_at[i] = best_r if best_run > 0 else 255
            next_any[i] = min_next

        self._best_region_at = best_region_at
        self._next_any_spot = next_any

    def _lazy_init(self) -> None:
        if self._initialized:
            return
        self._gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        if self._gap <= 0.0:
            self._gap = 1.0
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        self._min_switch_interval_steps = max(1, int(round(max(ro, self._gap) / self._gap)))
        self._finish_buffer = 2.0 * ro + 2.0 * self._gap
        self._pause_buffer = ro + self._gap
        self._initialized = True

    def _update_work_done(self) -> None:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return
        n = len(tdt)
        if n <= self._task_done_len:
            return
        # incremental sum
        s = 0.0
        for i in range(self._task_done_len, n):
            s += float(tdt[i])
        self._work_done += s
        self._task_done_len = n

    def _choose_target_region(self, idx: int) -> Optional[int]:
        if not self._have_traces or self._best_region_at is None or self._next_any_spot is None:
            return None
        if idx < 0:
            idx = 0
        if idx >= self._n_steps:
            return None

        br = int(self._best_region_at[idx])
        if br != 255:
            return br

        earliest = int(self._next_any_spot[idx])
        if earliest >= self._inf_idx or earliest >= self._n_steps:
            return None

        best_r = None
        best_run = -1
        for r in range(len(self._spot)):
            if int(self._next_spot[r][idx]) == earliest:
                rl = int(self._run_len[r][earliest])
                if rl > best_run:
                    best_run = rl
                    best_r = r
        return best_r

    def _predict_wait_steps_until_spot(self, step_idx: int, has_spot: bool) -> int:
        if has_spot:
            return 0
        if not self._have_traces or self._next_any_spot is None or self._best_region_at is None:
            return 1

        if step_idx < 0:
            step_idx = 0
        if step_idx >= self._n_steps:
            return 10**9

        next_any = int(self._next_any_spot[step_idx])
        if next_any >= self._inf_idx:
            return 10**9

        # If spot exists somewhere now but not in current region, our safest assumption is:
        # we can get onto it by switching and use it next step => wait 1 step.
        if next_any == step_idx:
            return 1
        return max(1, next_any - step_idx)

    def _maybe_switch_for_next_step(self, step_idx: int, has_spot: bool) -> None:
        if self._committed_on_demand:
            return
        if not self._have_traces:
            return
        if float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0) > 0.0:
            return

        cur = int(self.env.get_current_region())
        next_idx = step_idx + 1
        if next_idx < 0:
            next_idx = 0

        target = self._choose_target_region(next_idx)
        if target is None or target == cur:
            return

        # Only switch when either we don't have spot now, or spot won't continue next step.
        should = (not has_spot)
        if not should and next_idx < self._n_steps:
            if cur < len(self._spot) and not self._spot[cur][next_idx]:
                should = True

        if not should:
            return

        if step_idx - self._last_switch_step < self._min_switch_interval_steps:
            return

        self.env.switch_region(int(target))
        self._last_switch_step = step_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._update_work_done()

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        step_idx = int(elapsed // self._gap) if self._gap > 0 else 0

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        remaining_overhead = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)

        remaining_work = task_duration - self._work_done
        if remaining_work <= 0.0:
            return _CT_NONE

        remaining_time = deadline - elapsed
        if remaining_time <= 0.0:
            return ClusterType.ON_DEMAND

        # Switch region to increase chance of spot next step (positioning), when safe.
        self._maybe_switch_for_next_step(step_idx, has_spot)

        # Commit to on-demand only when needed to guarantee completion.
        min_finish_time_if_run = remaining_work + max(0.0, remaining_overhead)
        if remaining_time <= min_finish_time_if_run + self._finish_buffer:
            self._committed_on_demand = True

        if self._committed_on_demand:
            return ClusterType.ON_DEMAND

        if remaining_overhead > 0.0:
            if last_cluster_type == ClusterType.SPOT and has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        slack = remaining_time - remaining_work
        wait_steps = self._predict_wait_steps_until_spot(step_idx, has_spot=False)
        wait_seconds = float(wait_steps) * self._gap

        if slack >= wait_seconds + self._pause_buffer:
            return _CT_NONE

        return ClusterType.ON_DEMAND