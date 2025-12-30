import json
import math
from argparse import Namespace
from array import array
from typing import Any, List, Optional, Sequence, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multiregion_v1"

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

        self._commit_to_on_demand = False

        self._work_done = 0.0
        self._last_task_done_len = 0

        self._spot_avail: List[bytearray] = []
        self._spot_run_len: List[array] = []
        self._any_spot: Optional[bytearray] = None
        self._any_spot_suffix: Optional[array] = None
        self._no_spot_run_len: Optional[array] = None

        self._trace_enabled = False
        self._trace_mismatch_count = 0
        self._trace_index_mode = 0  # 0: env gap mapping, -1: disabled

        trace_files = config.get("trace_files") or []
        if isinstance(trace_files, (list, tuple)) and trace_files:
            traces = []
            for p in trace_files:
                try:
                    traces.append(self._load_trace_file(str(p)))
                except Exception:
                    traces.append(bytearray())
            min_len = min((len(t) for t in traces if t is not None), default=0)
            if min_len > 0:
                self._spot_avail = [bytearray(t[:min_len]) for t in traces]
                self._precompute_trace_helpers()
                self._trace_enabled = True

        return self

    def _load_trace_file(self, path: str) -> bytearray:
        with open(path, "r") as f:
            data = f.read().strip()
        if not data:
            return bytearray()

        def to_bool(v: Any) -> int:
            if isinstance(v, bool):
                return 1 if v else 0
            if v is None:
                return 0
            if isinstance(v, (int, float)):
                return 1 if v > 0 else 0
            s = str(v).strip().lower()
            if not s:
                return 0
            if s in ("1", "true", "t", "yes", "y", "available", "avail", "up"):
                return 1
            if s in ("0", "false", "f", "no", "n", "unavailable", "down"):
                return 0
            try:
                return 1 if float(s) > 0 else 0
            except Exception:
                return 0

        if data[0] in "[{":
            obj = json.loads(data)
            seq = None
            if isinstance(obj, list):
                seq = obj
            elif isinstance(obj, dict):
                for k in ("trace", "data", "availability", "avail", "spot", "values"):
                    if k in obj and isinstance(obj[k], list):
                        seq = obj[k]
                        break
                if seq is None:
                    for v in obj.values():
                        if isinstance(v, list):
                            seq = v
                            break
            if seq is None:
                return bytearray()
            out = bytearray(len(seq))
            for i, x in enumerate(seq):
                if isinstance(x, dict):
                    val = None
                    for k in ("available", "avail", "spot", "value", "up"):
                        if k in x:
                            val = x[k]
                            break
                    out[i] = to_bool(val)
                else:
                    out[i] = to_bool(x)
            return out

        lines = data.splitlines()
        vals = bytearray()
        for line in lines:
            s = line.strip()
            if not s:
                continue
            parts = s.replace("\t", " ").split(",")
            if len(parts) == 1:
                parts = s.split()
            token = parts[-1].strip() if parts else ""
            vals.append(to_bool(token))
        return vals

    def _precompute_trace_helpers(self) -> None:
        n = len(self._spot_avail[0])
        rcount = len(self._spot_avail)

        self._spot_run_len = []
        for r in range(rcount):
            run = array("I", [0]) * n
            cnt = 0
            avail = self._spot_avail[r]
            for t in range(n - 1, -1, -1):
                if avail[t]:
                    cnt += 1
                else:
                    cnt = 0
                run[t] = cnt
            self._spot_run_len.append(run)

        any_spot = bytearray(n)
        for r in range(rcount):
            a = self._spot_avail[r]
            for t in range(n):
                any_spot[t] |= a[t]
        self._any_spot = any_spot

        suffix = array("I", [0]) * (n + 1)
        for t in range(n - 1, -1, -1):
            suffix[t] = suffix[t + 1] + (1 if any_spot[t] else 0)
        self._any_spot_suffix = suffix

        no_run = array("I", [0]) * n
        cnt = 0
        for t in range(n - 1, -1, -1):
            if any_spot[t]:
                cnt = 0
            else:
                cnt += 1
            no_run[t] = cnt
        self._no_spot_run_len = no_run

    def _update_work_done_cache(self) -> None:
        td = self.task_done_time
        if td is None:
            self._work_done = 0.0
            self._last_task_done_len = 0
            return
        n = len(td)
        if n < self._last_task_done_len:
            self._work_done = float(sum(td))
            self._last_task_done_len = n
            return
        if n > self._last_task_done_len:
            s = 0.0
            for x in td[self._last_task_done_len :]:
                s += float(x)
            self._work_done += s
            self._last_task_done_len = n

    def _time_index(self) -> int:
        gap = float(self.env.gap_seconds)
        if gap <= 0:
            return 0
        return int(self.env.elapsed_seconds // gap)

    def _has_spot_trace(self, region: int, idx: int) -> bool:
        if not self._trace_enabled or self._trace_index_mode != 0:
            return False
        if region < 0 or region >= len(self._spot_avail):
            return False
        a = self._spot_avail[region]
        if idx < 0 or idx >= len(a):
            return False
        return bool(a[idx])

    def _any_spot_trace(self, idx: int) -> bool:
        if not self._trace_enabled or self._trace_index_mode != 0 or self._any_spot is None:
            return False
        if idx < 0 or idx >= len(self._any_spot):
            return False
        return bool(self._any_spot[idx])

    def _best_spot_region(self, idx: int, num_regions: int) -> Tuple[int, int]:
        best_r = -1
        best_len = 0
        rcount = min(num_regions, len(self._spot_avail))
        for r in range(rcount):
            if self._spot_avail[r][idx]:
                run_len = int(self._spot_run_len[r][idx]) if self._spot_run_len else 1
                if run_len > best_len:
                    best_len = run_len
                    best_r = r
        return best_r, best_len

    def _safe_switch_region(self, target_region: int) -> None:
        cur = self.env.get_current_region()
        if target_region == cur:
            return
        try:
            self.env.switch_region(int(target_region))
        except Exception:
            return

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_work_done_cache()

        work_left = float(self.task_duration) - float(self._work_done)
        if work_left <= 0.0:
            return ClusterType.NONE

        env = self.env
        gap = float(env.gap_seconds)
        if gap <= 0:
            gap = 1.0
        time_left = float(self.deadline) - float(env.elapsed_seconds)

        # Hard safety: if we can no longer risk waiting, commit to on-demand.
        od_overhead = float(self.remaining_restart_overhead) if last_cluster_type == ClusterType.ON_DEMAND else float(self.restart_overhead)
        safety_buffer = 2.0 * gap
        if time_left <= work_left + od_overhead + safety_buffer:
            self._commit_to_on_demand = True

        if self._commit_to_on_demand:
            return ClusterType.ON_DEMAND

        num_regions = 1
        try:
            num_regions = int(env.get_num_regions())
        except Exception:
            num_regions = 1

        idx = self._time_index()

        # Light trace consistency check (disable traces if clearly misaligned).
        if self._trace_enabled and self._trace_index_mode == 0:
            cur_r = 0
            try:
                cur_r = int(env.get_current_region())
            except Exception:
                cur_r = 0
            if 0 <= cur_r < len(self._spot_avail) and 0 <= idx < len(self._spot_avail[cur_r]):
                trace_has = bool(self._spot_avail[cur_r][idx])
                if trace_has != bool(has_spot):
                    self._trace_mismatch_count += 1
                    if self._trace_mismatch_count >= 8:
                        self._trace_index_mode = -1
                else:
                    if self._trace_mismatch_count > 0:
                        self._trace_mismatch_count -= 1

        trace_ok = self._trace_enabled and self._trace_index_mode == 0 and self._any_spot is not None
        if trace_ok and (idx < 0 or idx >= len(self._any_spot)):
            trace_ok = False

        # Without usable traces, simple single-region policy.
        if not trace_ok:
            if has_spot:
                return ClusterType.SPOT
            if time_left <= work_left + float(self.restart_overhead) + gap:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE

        any_spot_now = self._any_spot_trace(idx)
        cur_region = int(env.get_current_region()) if hasattr(env, "get_current_region") else 0
        cur_region = max(0, min(cur_region, num_regions - 1))

        # Compute minimum unavoidable on-demand based on union-spot upper bound (ignoring restarts).
        # Used primarily to decide whether to run OD during "no-spot-anywhere" gaps.
        any_suffix = self._any_spot_suffix
        max_spot_work = 0.0
        if any_suffix is not None and 0 <= idx < len(any_suffix):
            max_spot_work = float(any_suffix[idx]) * gap
        min_on_demand_needed = max(0.0, work_left - max_spot_work)

        overhead = float(self.restart_overhead)
        min_steps_to_make_spot_worth_starting = int(math.floor((overhead + gap - 1e-9) / gap)) + 1  # L*gap > overhead
        min_steps_to_switch_into_spot = min_steps_to_make_spot_worth_starting + 1  # get some real work after overhead

        if any_spot_now:
            best_region, best_run = self._best_spot_region(idx, num_regions)
            if best_region < 0:
                # Shouldn't happen since any_spot_now is true, but be safe.
                return ClusterType.NONE

            cur_has_spot = self._has_spot_trace(cur_region, idx) if 0 <= idx < len(self._spot_avail[0]) else False

            # Prefer staying if current region already has spot.
            target_region = cur_region if cur_has_spot else best_region

            # Avoid switching during an in-progress restart unless it is truly necessary.
            if (
                target_region != cur_region
                and float(self.remaining_restart_overhead) > 1e-9
                and float(self.remaining_restart_overhead) < overhead - 1e-9
            ):
                # Switching would reset remaining overhead upwards; skip.
                # If we cannot run spot here, just wait.
                return ClusterType.NONE

            if target_region != cur_region:
                # Only switch into spot if the available run is long enough to amortize restart.
                run_len_steps = int(self._spot_run_len[target_region][idx])
                if last_cluster_type != ClusterType.SPOT and run_len_steps < min_steps_to_switch_into_spot:
                    # Too short: better to wait (free) than pay overhead and maybe get negligible progress.
                    return ClusterType.NONE
                self._safe_switch_region(target_region)

            # If we're starting spot from non-spot, ensure the run is long enough.
            final_region = int(env.get_current_region()) if hasattr(env, "get_current_region") else target_region
            if not self._has_spot_trace(final_region, idx):
                return ClusterType.NONE

            if last_cluster_type != ClusterType.SPOT:
                run_len_steps = int(self._spot_run_len[final_region][idx])
                if run_len_steps < min_steps_to_make_spot_worth_starting:
                    return ClusterType.NONE

            return ClusterType.SPOT

        # No spot anywhere right now.
        if time_left <= work_left + float(self.restart_overhead) + gap:
            return ClusterType.ON_DEMAND

        if min_on_demand_needed <= 0.0:
            return ClusterType.NONE

        # If we truly need OD overall, prefer to do it during global no-spot segments,
        # but only if the no-spot run is long enough to amortize restart overhead.
        no_run = self._no_spot_run_len[idx] if self._no_spot_run_len is not None and 0 <= idx < len(self._no_spot_run_len) else 0
        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND
        if float(no_run) * gap >= overhead + gap:
            return ClusterType.ON_DEMAND
        return ClusterType.NONE