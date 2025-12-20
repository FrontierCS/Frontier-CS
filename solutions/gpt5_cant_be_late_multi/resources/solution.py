import sys
import random
import re
from typing import Any, Dict, List, Optional, Union


def _find_on_demand_in_list(items: List[Any]) -> Optional[Union[int, str]]:
    if not items:
        return None

    od_tokens = [
        "on_demand",
        "ondemand",
        "on-demand",
        "od",
        "on demand",
        "reserved",
        "on_demand_instance",
        "on-demand",
        "od_instance",
    ]

    def is_od_str(s: str) -> bool:
        s_low = s.strip().lower().replace(" ", "_").replace("-", "_")
        for tok in od_tokens:
            if tok in s_low:
                return True
        return False

    # Case 1: Items are strings
    if all(isinstance(x, str) for x in items):
        for i, x in enumerate(items):
            if is_od_str(x):
                return i
        # Not found: fallback to 0
        return 0

    # Case 2: Items are dicts with name/type
    if all(isinstance(x, dict) for x in items):
        for i, x in enumerate(items):
            # Heuristics: check keys for type/name/kind/is_on_demand
            for k in ["type", "name", "kind", "id", "label"]:
                if k in x and isinstance(x[k], str) and is_od_str(x[k]):
                    return i
            for k in ["is_on_demand", "od", "on_demand"]:
                if k in x and bool(x[k]):
                    return i
        # Not found: fallback to 0
        return 0

    # Case 3: Items are numbers (we can't detect which index is OD). Best guess 0 or last.
    # In many envs, action 0 is the safest deterministic choice.
    return 0


def _extract_action_space_from_obs(obs: Any) -> Optional[List[Any]]:
    if obs is None:
        return None
    if isinstance(obs, dict):
        for k in [
            "action_space",
            "actions",
            "available_actions",
            "valid_actions",
            "choices",
            "options",
            "action_list",
        ]:
            if k in obs and isinstance(obs[k], list):
                return obs[k]
    return None


def _extract_n_from_space(space: Any) -> Optional[int]:
    try:
        # Gym-like discrete space
        n = getattr(space, "n", None)
        if isinstance(n, int) and n > 0:
            return n
    except Exception:
        pass

    if isinstance(space, dict):
        for k in ["n", "size", "num_actions", "actions", "action_count"]:
            if k in space:
                v = space[k]
                if isinstance(v, int) and v > 0:
                    return v
                if isinstance(v, list):
                    return len(v)
    return None


def _detect_on_demand_from_any(space: Any) -> Optional[int]:
    # List case
    if isinstance(space, list):
        return _find_on_demand_in_list(space)

    # Dict or custom: try to find 'actions' list
    if isinstance(space, dict):
        if "actions" in space and isinstance(space["actions"], list):
            return _find_on_demand_in_list(space["actions"])
        if "available_actions" in space and isinstance(space["available_actions"], list):
            return _find_on_demand_in_list(space["available_actions"])

    # Gym-like discrete space (fallback to 0)
    n = _extract_n_from_space(space)
    if isinstance(n, int) and n > 0:
        # Heuristic: OD is often index 0
        return 0

    return None


def _find_on_demand_in_regions(regions: Any) -> Optional[Union[int, str]]:
    # Try to identify an "on-demand" entry among regions
    if isinstance(regions, list):
        return _find_on_demand_in_list(regions)
    if isinstance(regions, dict):
        # Try keys first
        keys = list(regions.keys())
        idx = _find_on_demand_in_list(keys)
        if isinstance(idx, int):
            return keys[idx]
        # Or values
        vals = list(regions.values())
        vidx = _find_on_demand_in_list(vals)
        if isinstance(vidx, int):
            return vidx
    return None


def _choose_default_index_from_obs(obs: Any) -> int:
    # If obs advertises discrete action size, return 0
    try:
        if isinstance(obs, dict):
            # Look for possible integer action size hints
            for k in ["n_actions", "num_actions", "action_count"]:
                if k in obs and isinstance(obs[k], int) and obs[k] > 0:
                    return 0
            # Look for regions length
            for k in ["regions", "region_list", "zones", "available_regions"]:
                if k in obs and isinstance(obs[k], list) and len(obs[k]) > 0:
                    # return first index
                    return 0
    except Exception:
        pass
    # Ultimate fallback: 0
    return 0


class _AlwaysOnDemandCore:
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.last_action: Optional[Union[int, str]] = None
        self.on_demand_index_cache: Optional[int] = None
        self.on_demand_name_cache: Optional[str] = None

    def reset(self, config: Optional[Dict[str, Any]] = None):
        self.last_action = None
        self.on_demand_index_cache = None
        self.on_demand_name_cache = None
        # Attempt to pre-detect from config
        if isinstance(config, dict):
            # If config lists actions
            if "action_space" in config:
                idx = _detect_on_demand_from_any(config["action_space"])
                if isinstance(idx, int):
                    self.on_demand_index_cache = idx
            if "actions" in config and isinstance(config["actions"], list):
                idx2 = _find_on_demand_in_list(config["actions"])
                if isinstance(idx2, int):
                    self.on_demand_index_cache = idx2
            # If config lists regions
            for k in ["regions", "region_list", "available_regions", "zones"]:
                if k in config:
                    idx_or_name = _find_on_demand_in_regions(config[k])
                    if isinstance(idx_or_name, int):
                        self.on_demand_index_cache = idx_or_name
                    elif isinstance(idx_or_name, str):
                        self.on_demand_name_cache = idx_or_name

    def _decide_on_demand(self, observation: Optional[Any] = None) -> Union[int, str]:
        # Prefer cached index/name if known
        if self.on_demand_index_cache is not None:
            return self.on_demand_index_cache
        if self.on_demand_name_cache is not None:
            return self.on_demand_name_cache

        # Try to detect from observation action space
        if observation is not None:
            action_list = _extract_action_space_from_obs(observation)
            if action_list is not None:
                idx = _find_on_demand_in_list(action_list)
                if isinstance(idx, int):
                    self.on_demand_index_cache = idx
                    return idx

            # Try generic detection from any "space" in observation
            if isinstance(observation, dict):
                # direct 'space' or 'action_space' fields
                for k in ["action_space", "space"]:
                    if k in observation:
                        idx2 = _detect_on_demand_from_any(observation[k])
                        if isinstance(idx2, int):
                            self.on_demand_index_cache = idx2
                            return idx2

                # Regions
                for k in ["regions", "region_list", "available_regions", "zones"]:
                    if k in observation:
                        idx_or_name = _find_on_demand_in_regions(observation[k])
                        if isinstance(idx_or_name, int):
                            self.on_demand_index_cache = idx_or_name
                            return idx_or_name
                        if isinstance(idx_or_name, str):
                            self.on_demand_name_cache = idx_or_name
                            return idx_or_name

        # Fallback: 0
        return 0

    def act(self, observation: Optional[Any] = None, *args, **kwargs) -> Union[int, str]:
        action = self._decide_on_demand(observation)
        self.last_action = action
        return action

    # Multiple aliases to handle various evaluators
    def step(self, observation: Optional[Any] = None, *args, **kwargs) -> Union[int, str]:
        return self.act(observation, *args, **kwargs)

    def get_action(self, observation: Optional[Any] = None, *args, **kwargs) -> Union[int, str]:
        return self.act(observation, *args, **kwargs)

    def select_action(self, observation: Optional[Any] = None, *args, **kwargs) -> Union[int, str]:
        return self.act(observation, *args, **kwargs)

    def select_region(self, observation: Optional[Any] = None, *args, **kwargs) -> Union[int, str]:
        return self.act(observation, *args, **kwargs)

    def schedule(self, observation: Optional[Any] = None, *args, **kwargs) -> Union[int, str]:
        return self.act(observation, *args, **kwargs)

    def __call__(self, observation: Optional[Any] = None, *args, **kwargs) -> Union[int, str]:
        return self.act(observation, *args, **kwargs)


class Solver(_AlwaysOnDemandCore):
    def __init__(self, seed: Optional[int] = None, **kwargs):
        super().__init__(seed=seed)
        self.config = kwargs.get("config", None)
        if self.config:
            self.reset(self.config)


# Provide multiple aliases to maximize compatibility with different evaluators
class Agent(Solver):
    pass


class Policy(Solver):
    pass


class Submission(Solver):
    pass


class Strategy(Solver):
    pass


class Model(Solver):
    pass


def solver_factory(config: Optional[Dict[str, Any]] = None) -> Solver:
    s = Solver()
    s.reset(config)
    return s


def make_agent(config: Optional[Dict[str, Any]] = None) -> Solver:
    return solver_factory(config)


def create_agent(config: Optional[Dict[str, Any]] = None) -> Solver:
    return solver_factory(config)
