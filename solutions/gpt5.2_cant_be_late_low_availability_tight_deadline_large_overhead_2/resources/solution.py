import argparse
import json
import math
import os
import re
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_adaptive_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass

        self.args = args
        self._reset_internal()

    def _reset_internal(self):
        self._inited = False

        self._prev_has_spot: Optional[bool] = None
        self._steps_observed = 0
        self._spot_steps = 0
        self._avail_to_unavail = 0
        self._unavail_to_avail = 0

        self._spot_up_streak = 0
        self._spot_down_streak = 0

        self._od_locked = False
        self._cooldown_steps = 0
        self._switches = 0

        self._last_valid_done = 0.0

        self._price_od = 3.06
        self._price_spot = 0.97

    def solve(self, spec_path: str) -> "Solution":
        self._reset_internal()
        self._try_load_prices(spec_path)
        return self

    def _try_load_prices(self, spec_path: str) -> None:
        if not spec_path:
            return
        try:
            if os.path.exists(spec_path):
                with open(spec_path, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                return
        except Exception:
            return

        try:
            if spec_path.endswith(".json"):
                data = json.loads(content)
                self._extract_prices_from_obj(data)
                return
        except Exception:
            pass

        try:
            # Very lightweight key: value extraction for YAML-like specs.
            # Accepts: spot_price, on_demand_price, ondemand_price, od_price.
            def _find_float(keys):
                for k in keys:
                    m = re.search(rf"(?im)^\s*{re.escape(k)}\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*$", content)
                    if m:
                        try:
                            return float(m.group(1))
                        except Exception:
                            pass
                return None

            spot = _find_float(["spot_price", "price_spot", "spot"])
            od = _find_float(["on_demand_price", "ondemand_price", "od_price", "price_on_demand", "on_demand"])
            if spot is not None and spot > 0:
                self._price_spot = spot
            if od is not None and od > 0:
                self._price_od = od
        except Exception:
            return

    def _extract_prices_from_obj(self, obj: Any) -> None:
        # Try multiple common nesting patterns
        if not isinstance(obj, dict):
            return

        def _dig(d, keys):
            cur = d
            for k in keys:
                if isinstance(cur, dict) and k in cur:
                    cur = cur[k]
                else:
                    return None
            return cur

        candidates = [
            ("spot_price",),
            ("price_spot",),
            ("prices", "spot"),
            ("cost", "spot"),
            ("on_demand_price",),
            ("ondemand_price",),
            ("od_price",),
            ("price_on_demand",),
            ("prices", "on_demand"),
            ("prices", "ondemand"),
            ("cost", "on_demand"),
        ]

        found_spot = None
        found_od = None

        for path in candidates:
            v = _dig(obj, path)
            if isinstance(v, (int, float)) and v > 0:
                key = path[-1]
                if "spot" in key:
                    found_spot = float(v)
                elif "demand" in key or key in ("od_price", "ondemand"):
                    found_od = float(v)

        if found_spot is not None:
            self._price_spot = found_spot
        if found_od is not None:
            self._price_od = found_od

    def _compute_done_seconds(self) -> float:
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        tdt = getattr(self, "task_done_time", None)

        done = None

        try:
            if tdt is None:
                done = None
            elif isinstance(tdt, (int, float)):
                done = float(tdt)
            elif isinstance(tdt, dict):
                for k in ("done", "duration", "total", "completed", "work_done_seconds"):
                    v = tdt.get(k, None)
                    if isinstance(v, (int, float)):
                        done = float(v)
                        break
            elif isinstance(tdt, (list, tuple)):
                if len(tdt) == 0:
                    done = 0.0
                else:
                    # If list of tuples/pairs: sum intervals.
                    if all(isinstance(x, (list, tuple)) and len(x) == 2 for x in tdt):
                        total = 0.0
                        for a, b in tdt:
                            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                                if b > a:
                                    total += float(b - a)
                        done = total
                    # If list of numbers: could be per-segment or cumulative.
                    elif all(isinstance(x, (int, float)) for x in tdt):
                        arr = [float(x) for x in tdt]
                        # Detect monotonic cumulative series
                        is_mono = True
                        for i in range(1, len(arr)):
                            if arr[i] + 1e-9 < arr[i - 1]:
                                is_mono = False
                                break
                        if is_mono and task_duration > 0 and 0 <= arr[-1] <= task_duration * 1.02:
                            done = arr[-1]
                        else:
                            s = sum(arr)
                            if task_duration <= 0:
                                done = arr[-1] if is_mono else s
                            else:
                                # Prefer sum if it's plausible
                                if 0 <= s <= task_duration * 1.10:
                                    done = s
                                elif 0 <= arr[-1] <= task_duration * 1.10:
                                    done = arr[-1]
                                else:
                                    done = min(s, arr[-1])
                    else:
                        # Unknown list format
                        done = None
        except Exception:
            done = None

        if done is None:
            return self._last_valid_done

        if not math.isfinite(done):
            return self._last_valid_done

        if done < 0:
            done = 0.0
        if task_duration > 0:
            done = max(0.0, min(done, task_duration))
        self._last_valid_done = done
        return done

    def _estimate_stats(self, gap: float) -> tuple[float, float, float]:
        # Returns: p_avail, mean_uptime_seconds, mean_downtime_seconds
        # Use Beta(2,2) prior
        steps = self._steps_observed
        spot_steps = self._spot_steps
        p_avail = (spot_steps + 2.0) / (steps + 4.0) if steps >= 0 else 0.5

        # Transitions with smoothing
        # q = P(available->unavailable | available)
        q = (self._avail_to_unavail + 1.0) / (spot_steps + 2.0) if spot_steps >= 0 else 0.5
        # p10 = P(unavailable->available | unavailable)
        unavail_steps = max(0, steps - spot_steps)
        p10 = (self._unavail_to_avail + 1.0) / (unavail_steps + 2.0) if unavail_steps >= 0 else 0.5

        # Mean run lengths in steps (geometric), capped for stability
        mean_u_steps = 1.0 / max(1e-6, min(1.0, q))
        mean_d_steps = 1.0 / max(1e-6, min(1.0, p10))

        # Convert to seconds
        mean_uptime = mean_u_steps * gap
        mean_downtime = mean_d_steps * gap

        # Additional sanity cap
        cap = 24.0 * 3600.0
        if mean_uptime > cap:
            mean_uptime = cap
        if mean_downtime > cap:
            mean_downtime = cap

        return p_avail, mean_uptime, mean_downtime

    def _should_lock_od(self, time_left: float, remaining_work: float, slack: float, gap: float) -> bool:
        h = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        # If already locked, keep locked
        if self._od_locked:
            return True

        # If impossible, lock to OD (best effort)
        if time_left <= 0:
            return True

        # Deadline safety: near the end, avoid preemption risk entirely
        lock_slack = max(4.0 * h + gap, 45.0 * 60.0)  # ~1h typical with given params
        final_buffer = max(2.0 * h + gap, 20.0 * 60.0)

        if slack <= lock_slack:
            return True
        if time_left <= remaining_work + final_buffer:
            return True

        # If spot is extremely unstable (mean uptime not exceeding overhead by enough), lock
        p_avail, mean_uptime, _ = self._estimate_stats(gap)
        if h > 0:
            if mean_uptime <= max(1.5 * h, 10.0 * 60.0) and p_avail < 0.5:
                return True

        # If we've already switched a lot relative to remaining slack, lock.
        # Very rough: each switch can burn up to one overhead of non-progress time.
        if h > 0 and slack > 0:
            if self._switches * h >= 0.6 * slack:
                return True

        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = getattr(self, "env", None)
        elapsed = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(env, "gap_seconds", 60.0) or 60.0)

        # Update availability statistics based on last observed has_spot
        if not self._inited:
            self._inited = True
            self._prev_has_spot = has_spot
            self._spot_up_streak = 1 if has_spot else 0
            self._spot_down_streak = 0 if has_spot else 1
        else:
            prev = bool(self._prev_has_spot)
            cur = bool(has_spot)

            self._steps_observed += 1
            if prev:
                self._spot_steps += 1

            if prev and not cur:
                self._avail_to_unavail += 1
            elif (not prev) and cur:
                self._unavail_to_avail += 1

            if cur:
                self._spot_up_streak += 1
                self._spot_down_streak = 0
            else:
                self._spot_down_streak += 1
                self._spot_up_streak = 0

            self._prev_has_spot = cur

        if self._cooldown_steps > 0:
            self._cooldown_steps -= 1

        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        time_left = deadline - elapsed

        done = self._compute_done_seconds()
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        remaining_work = max(0.0, task_duration - done)

        if remaining_work <= 0.0:
            return ClusterType.NONE

        slack = time_left - remaining_work

        if self._should_lock_od(time_left, remaining_work, slack, gap):
            self._od_locked = True
            chosen = ClusterType.ON_DEMAND
            if last_cluster_type in (ClusterType.SPOT, ClusterType.ON_DEMAND) and chosen in (ClusterType.SPOT, ClusterType.ON_DEMAND) and chosen != last_cluster_type:
                self._switches += 1
            return chosen

        # Not locked: decide using a sticky OD-with-opportunistic-spot policy.
        h = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        _, mean_uptime, _ = self._estimate_stats(gap)

        # Minimum expected uptime to consider switching from OD to SPOT.
        min_uptime = max(3.0 * h, 30.0 * 60.0)  # >= 30 minutes and >= 3x overhead
        min_slack_for_switch = max(2.5 * h + gap, 30.0 * 60.0)  # need room to absorb at least one disruption

        confirm_steps = 2

        # If we are on spot, keep using it as long as it's available (unless lock triggered above).
        if last_cluster_type == ClusterType.SPOT:
            if has_spot:
                return ClusterType.SPOT
            # Spot not available -> fall back to OD and start cooldown to avoid thrashing.
            self._cooldown_steps = max(self._cooldown_steps, 2)
            self._switches += 1
            return ClusterType.ON_DEMAND

        # If spot unavailable now, we typically must use OD to meet the tight deadline.
        if not has_spot:
            return ClusterType.ON_DEMAND

        # Spot is available now, last cluster not spot.
        # Consider switching from OD to SPOT if it's likely to be stable and we have slack.
        if last_cluster_type == ClusterType.ON_DEMAND:
            if self._cooldown_steps > 0:
                return ClusterType.ON_DEMAND
            if slack < min_slack_for_switch:
                return ClusterType.ON_DEMAND
            if self._spot_up_streak < confirm_steps:
                return ClusterType.ON_DEMAND
            if mean_uptime < min_uptime:
                return ClusterType.ON_DEMAND

            self._switches += 1
            return ClusterType.SPOT

        # last_cluster_type == NONE (or other) and spot is available
        # Start on spot unless slack is extremely tight (handled by lock above).
        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
