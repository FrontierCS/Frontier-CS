import json
import math
import os
from argparse import Namespace
from array import array
from typing import Any, List, Optional, Sequence, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path, "r") as f:
            config = json.load(f)

        self._config = config
        self._trace_files = list(config.get("trace_files", []))

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self._raw_traces: List[List[int]] = []
        for p in self._trace_files:
            try:
                self._raw_traces.append(self._load_trace(p))
            except Exception:
                self._raw_traces.append([])

        self._initialized = False
        self._committed_to_on_demand = False

        self._cached_done = 0.0
        self._cached_len = 0

        self._spot: List[bytearray] = []
        self._run_len: List[array] = []
        self._any_spot_suffix: array = array("I")
        self._plan_region: bytearray = bytearray()
        self._horizon_steps = 0

        self._offset_candidates = list(range(-5, 6))
        self._offset_scores = [0] * len(self._offset_candidates)
        self._offset_samples = 0
        self._trace_offset = 0
        self._trace_offset_frozen = False

        self._last_switch_env_idx = -10**9

        return self

    @staticmethod
    def _coerce_bool(x: Any) -> int:
        if x is None:
            return 0
        if isinstance(x, bool):
            return int(x)
        if isinstance(x, (int, float)):
            return 1 if x > 0 else 0
        if isinstance(x, str):
            s = x.strip().lower()
            if not s:
                return 0
            if s in ("1", "true", "t", "yes", "y", "up", "available", "avail"):
                return 1
            if s in ("0", "false", "f", "no", "n", "down", "unavailable"):
                return 0
            try:
                return 1 if float(s) > 0 else 0
            except Exception:
                return 0
        if isinstance(x, dict):
            for k in ("spot", "availability", "avail", "available", "up", "value", "state"):
                if k in x:
                    return Solution._coerce_bool(x[k])
            if x:
                try:
                    return Solution._coerce_bool(next(iter(x.values())))
                except Exception:
                    return 0
            return 0
        if isinstance(x, (list, tuple)) and x:
            return Solution._coerce_bool(x[-1])
        return 0

    def _load_trace(self, path: str) -> List[int]:
        if not path:
            return []
        with open(path, "r") as f:
            content = f.read()
        s = content.strip()
        if not s:
            return []

        obj: Any = None
        try:
            obj = json.loads(s)
        except Exception:
            obj = None

        vals: List[Any] = []
        if isinstance(obj, dict):
            for k in ("trace", "traces", "data", "availability", "avail", "spot", "values"):
                if k in obj and isinstance(obj[k], list):
                    vals = obj[k]
                    break
            if not vals:
                if "records" in obj and isinstance(obj["records"], list):
                    vals = obj["records"]
                elif "items" in obj and isinstance(obj["items"], list):
                    vals = obj["items"]
                else:
                    for v in obj.values():
                        if isinstance(v, list):
                            vals = v
                            break
        elif isinstance(obj, list):
            vals = obj

        if vals:
            return [self._coerce_bool(v) for v in vals]

        out: List[int] = []
        lines = s.splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                continue
            parts = line.split(",")
            if len(parts) == 1:
                parts = line.split()
            if not parts:
                continue
            token = parts[-1].strip()
            if token.lower() in ("availability", "avail", "spot", "state", "value"):
                continue
            out.append(self._coerce_bool(token))
        return out

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return

        num_regions = int(self.env.get_num_regions())
        gap = float(self.env.gap_seconds)
        if gap <= 0:
            gap = 1.0

        horizon = int(math.ceil(float(self.deadline) / gap)) + 8
        if horizon < 16:
            horizon = 16
        self._horizon_steps = horizon

        self._spot = []
        self._run_len = []

        for r in range(num_regions):
            raw = self._raw_traces[r] if r < len(self._raw_traces) else []
            arr = bytearray(horizon)
            n = min(len(raw), horizon)
            if n:
                arr[:n] = bytes((1 if raw[i] else 0 for i in range(n)))
            self._spot.append(arr)

        for r in range(num_regions):
            rl = array("I", [0]) * horizon
            a = self._spot[r]
            last = 0
            for t in range(horizon - 1, -1, -1):
                if a[t]:
                    last += 1
                    rl[t] = last
                else:
                    last = 0
                    rl[t] = 0
            self._run_len.append(rl)

        any_spot = bytearray(horizon)
        for t in range(horizon):
            v = 0
            for r in range(num_regions):
                v |= self._spot[r][t]
                if v:
                    break
            any_spot[t] = 1 if v else 0

        suffix = array("I", [0]) * (horizon + 1)
        for t in range(horizon - 1, -1, -1):
            suffix[t] = suffix[t + 1] + (1 if any_spot[t] else 0)
        self._any_spot_suffix = suffix

        self._plan_region = self._compute_region_plan(num_regions, horizon, gap)

        self._initialized = True

    def _compute_region_plan(self, num_regions: int, horizon: int, gap: float) -> bytearray:
        if num_regions <= 1:
            return bytearray([0]) * horizon

        alpha = float(self.restart_overhead) / float(gap) if gap > 0 else 0.0
        alpha = max(0.0, alpha) * 1.5

        dp_prev = [0.0] * num_regions
        dp = [0.0] * num_regions
        back = bytearray(horizon * num_regions)

        for r in range(num_regions):
            dp_prev[r] = float(self._spot[r][0])

        for r in range(num_regions):
            back[r] = r

        for t in range(1, horizon):
            best1 = 0
            best2 = 0
            v1 = dp_prev[0]
            v2 = float("-inf")
            for r in range(1, num_regions):
                v = dp_prev[r]
                if v > v1:
                    best2, v2 = best1, v1
                    best1, v1 = r, v
                elif v > v2:
                    best2, v2 = r, v

            base_best_val = v1
            base_second_val = v2

            for r in range(num_regions):
                stay_val = dp_prev[r]
                if best1 == r:
                    switch_from = best2
                    switch_val = base_second_val - alpha if base_second_val != float("-inf") else float("-inf")
                else:
                    switch_from = best1
                    switch_val = base_best_val - alpha

                if stay_val >= switch_val:
                    prev = r
                    base = stay_val
                else:
                    prev = switch_from
                    base = switch_val

                back[t * num_regions + r] = prev
                dp[r] = base + (1.0 if self._spot[r][t] else 0.0)

            dp_prev, dp = dp, dp_prev

        end_r = 0
        bestv = dp_prev[0]
        for r in range(1, num_regions):
            if dp_prev[r] > bestv:
                bestv = dp_prev[r]
                end_r = r

        plan = bytearray(horizon)
        cur = end_r
        for t in range(horizon - 1, -1, -1):
            plan[t] = cur
            cur = back[t * num_regions + cur]
        return plan

    def _update_cached_work_done(self) -> float:
        td = self.task_done_time
        n = len(td)
        if n < self._cached_len:
            self._cached_done = sum(float(x) for x in td)
            self._cached_len = n
            return self._cached_done
        if n > self._cached_len:
            self._cached_done += sum(float(x) for x in td[self._cached_len : n])
            self._cached_len = n
        return self._cached_done

    def _env_step_idx(self) -> int:
        gap = float(self.env.gap_seconds)
        if gap <= 0:
            return 0
        e = float(self.env.elapsed_seconds)
        if e <= 0:
            return 0
        return int(e // gap)

    def _trace_idx(self, env_idx: int) -> int:
        idx = env_idx + int(self._trace_offset)
        if idx < 0:
            return 0
        if idx >= self._horizon_steps:
            return self._horizon_steps - 1
        return idx

    def _calibrate_offset(self, env_idx: int, region: int, has_spot: bool) -> None:
        if self._trace_offset_frozen or not self._spot:
            return
        self._offset_samples += 1
        for i, off in enumerate(self._offset_candidates):
            idx = env_idx + off
            if idx < 0:
                idx2 = 0
            elif idx >= self._horizon_steps:
                idx2 = self._horizon_steps - 1
            else:
                idx2 = idx
            pred = bool(self._spot[region][idx2])
            if pred == bool(has_spot):
                self._offset_scores[i] += 1

        if self._offset_samples >= 20:
            best_i = 0
            best_s = self._offset_scores[0]
            for i in range(1, len(self._offset_scores)):
                if self._offset_scores[i] > best_s:
                    best_s = self._offset_scores[i]
                    best_i = i
            self._trace_offset = self._offset_candidates[best_i]

        if self._offset_samples >= 60:
            self._trace_offset_frozen = True

    def _best_spot_region_now(self, idx: int) -> Tuple[int, int]:
        num_regions = int(self.env.get_num_regions())
        best_r = -1
        best_len = 0
        for r in range(num_regions):
            if self._spot[r][idx]:
                l = int(self._run_len[r][idx])
                if l > best_len:
                    best_len = l
                    best_r = r
        return best_r, best_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_initialized()

        gap = float(self.env.gap_seconds)
        if gap <= 0:
            gap = 1.0

        env_idx = self._env_step_idx()
        cur_region = int(self.env.get_current_region())
        self._calibrate_offset(env_idx, cur_region, has_spot)
        idx = self._trace_idx(env_idx)

        done = self._update_cached_work_done()
        remaining_work = float(self.task_duration) - float(done)
        if remaining_work <= 0:
            return ClusterType.NONE

        remaining_time = float(self.deadline) - float(self.env.elapsed_seconds)
        if remaining_time <= 0:
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        slack = remaining_time - remaining_work

        if self._committed_to_on_demand:
            return ClusterType.ON_DEMAND

        r_over = float(self.remaining_restart_overhead) if self.remaining_restart_overhead is not None else 0.0
        restart_overhead = float(self.restart_overhead)

        # If we can finish on current spot without any further interruptions, do it.
        if has_spot:
            rl = int(self._run_len[cur_region][idx]) if cur_region < len(self._run_len) else 0
            if float(rl) * gap >= remaining_work and remaining_time >= remaining_work:
                return ClusterType.SPOT

        # If time is tight, commit to on-demand (avoid further restarts/switches).
        need_overhead_to_start_od = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead
        slack_after_od_start = remaining_time - need_overhead_to_start_od - remaining_work
        if slack_after_od_start <= (2.0 * restart_overhead + gap):
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # During restart overhead, avoid switching; prefer cheap progress if possible, otherwise idle.
        if r_over > 0:
            if has_spot:
                return ClusterType.SPOT
            # Only idle if we have ample slack; otherwise, make progress on on-demand.
            if slack >= (2.0 * gap + restart_overhead):
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        num_regions = int(self.env.get_num_regions())
        planned_r = int(self._plan_region[idx]) if self._plan_region else cur_region
        planned_r = planned_r if 0 <= planned_r < num_regions else cur_region

        # If spot is available somewhere, run spot (possibly switch regions if worthwhile).
        best_r, best_len = self._best_spot_region_now(idx)
        if best_r != -1:
            # Prefer planned region if it has spot and isn't much worse than the best.
            target = best_r
            if planned_r != best_r and self._spot[planned_r][idx]:
                pr_len = int(self._run_len[planned_r][idx])
                if pr_len >= max(1, int(0.8 * best_len)):
                    target = planned_r

            # If current region has spot, avoid switching unless big benefit.
            if has_spot:
                cur_len = int(self._run_len[cur_region][idx]) if cur_region < len(self._run_len) else 0
                if cur_region != target:
                    benefit = float(best_len - cur_len) * gap
                    can_switch = (
                        slack > (3.0 * restart_overhead + gap)
                        and benefit > (2.0 * restart_overhead + 0.5 * gap)
                        and float(best_len) * gap >= (restart_overhead + gap)
                        and (env_idx - self._last_switch_env_idx) >= 2
                    )
                    if can_switch and 0 <= target < num_regions and self._spot[target][idx]:
                        self.env.switch_region(target)
                        self._last_switch_env_idx = env_idx
                return ClusterType.SPOT

            # Current region has no spot; consider switching to a region with a decent run.
            if cur_region != target:
                can_switch = (
                    slack > (3.0 * restart_overhead + gap)
                    and float(best_len) * gap >= (restart_overhead + gap)
                    and (env_idx - self._last_switch_env_idx) >= 2
                )
                if can_switch and 0 <= target < num_regions and self._spot[target][idx]:
                    self.env.switch_region(target)
                    self._last_switch_env_idx = env_idx
                    return ClusterType.SPOT

            # If we can't/shouldn't switch, idle rather than pay on-demand (still plenty of slack here).
            if slack >= gap + restart_overhead:
                return ClusterType.NONE
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # No spot anywhere now: idle if we can afford it; otherwise commit to on-demand.
        if slack >= (gap + restart_overhead):
            return ClusterType.NONE

        self._committed_to_on_demand = True
        return ClusterType.ON_DEMAND
