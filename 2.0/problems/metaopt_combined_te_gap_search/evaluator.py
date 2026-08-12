"""Evaluator for the MetaOpt budgeted combined-TE gap search task."""
from __future__ import annotations

import hashlib
import heapq
import importlib.util
import itertools
import json
import math
import os
import random
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Iterable

SUITE_REVISION = 3
CASES_PER_TOPOLOGY = 5
QUERY_BUDGET = 256
DENSITY_LIMIT = 9
LEVELS = (0.0, 6.0, 18.0)
PINNING_THRESHOLD = 6.0
POP_PARTITIONS = 3
PATH_LIMIT = 4
CASE_TIMEOUT_SECONDS = 30
CASE_CPU_LIMIT_SECONDS = CASE_TIMEOUT_SECONDS * 4
BUILD_TIMEOUT_SECONDS = 240
MAX_SUBMISSION_BYTES = 2_000_000
MAX_FILES = 96
MAX_OUTPUT_BYTES = 65_536
MAX_CHILD_PROCESSES = 64
MAX_CHILD_FILE_DESCRIPTORS = 64
FLOW_TOLERANCE = 1e-7
SCORE_SCALE = 40.0
REFERENCE_TIME_LIMIT_SECONDS = 10.0
REFERENCE_WORK_LIMIT = 6.0
REFERENCE_THREADS = 4
REFERENCE_CACHE_TAG = "tegap-v3-paper-global-gurobi13-r2"
_REFERENCE_CACHE_OVERRIDE = os.environ.get("METAOPT_REFERENCE_CACHE_PATH")
REFERENCE_CACHE_PATH = Path(_REFERENCE_CACHE_OVERRIDE) if _REFERENCE_CACHE_OVERRIDE else None
_REFERENCE_DATA: dict[str, dict[str, Any]] = {}
_LAST_INTERNAL_DIAGNOSTICS: dict[str, Any] = {}

# Python strategies are reviewer-only artifacts. The real judge relocates a file
# submission to a temporary name, so authenticate its contents rather than its
# path. Candidate submissions remain C# project directories.
APPROVED_STRATEGY_HASHES = {
    "b3751006330c062d1e4a7377e557b6245266843b64a13fdcd7c2612ad15266ba": "reference",
    "18fde43ae3fb5bcee76d5a78d7d2e3872950046c53ae868570b726389b31fc1e": "baseline_clustered",
    "66b70cfc4667bba150770eb12c9f41a0f9eb59d9df03418e26334d7e277b6e44": "baseline_naive",
    "610df5afc5020b3aeac5e72b06a0ee345c4fcab141ea2c9d6b0294740571d7f6": "baseline_mid",
    "a357d045d94164707faec7b34fe8a174dda1ffe5b6b6ff3d38da56a47d8be488": "baseline_strong",
}

# Computed from the exact Harbor-staged /app tree. The editable search file,
# optional Candidate/ helpers, build artifacts, and Harbor-owned root workflow
# files are deliberately absent from the versioned tree digest.
LOCKED_TREE_HASH = "afcb69e01ba74e8cd54fc0b1d3564766e141cbee04f739abfb7fe19decf11720"
LOCKED_TREE_DOMAIN = b"metaopt-locked-tree-v2\0"
HARBOR_RUNTIME_FILES = frozenset({
    "AGENT.md",
    "readme",
    "submission_config.json",
    "submit.py",
    "submit.sh",
    "submissions.py",
    "submissions.sh",
    "wait_submission.py",
    "wait_submission.sh",
    "cancel_submission.py",
    "cancel_submission.sh",
})

TOPOLOGY_EDGES: dict[str, tuple[tuple[int, int], ...]] = {
    # MetaOpt/Topologies/swan.json
    "swan": (
        (0, 1), (0, 3), (1, 0), (1, 2), (2, 1), (2, 3), (2, 4), (2, 5),
        (3, 0), (3, 2), (3, 4), (3, 5), (4, 2), (4, 3), (4, 5), (4, 6),
        (5, 3), (5, 2), (5, 4), (5, 7), (6, 4), (6, 7), (7, 5), (7, 6),
    ),
    # MetaOpt/Topologies/abilene.json
    "abilene": (
        (0, 1), (0, 2), (1, 0), (1, 2), (1, 5), (2, 1), (2, 0), (2, 3),
        (3, 2), (3, 4), (3, 6), (4, 3), (4, 5), (4, 7), (5, 1), (5, 4),
        (6, 3), (6, 7), (6, 8), (7, 4), (7, 6), (7, 9), (8, 6), (8, 9),
        (9, 8), (9, 7),
    ),
    # MetaOpt/Topologies/b4-teavar.json
    "b4": (
        (0, 1), (0, 2), (1, 0), (1, 4), (2, 0), (2, 3), (2, 5), (4, 1),
        (4, 3), (4, 5), (3, 2), (3, 4), (3, 6), (3, 7), (5, 2), (5, 4),
        (5, 6), (5, 7), (6, 3), (6, 5), (6, 7), (6, 10), (7, 3), (7, 5),
        (7, 6), (7, 9), (10, 6), (10, 8), (10, 9), (10, 11), (9, 7),
        (9, 8), (9, 10), (9, 11), (8, 9), (8, 10), (11, 9), (11, 10),
    ),
}

_PRIVATE_SUITE_KEYS = {
    "agent": bytes.fromhex("6a18d914615f09234dc51a306580ff27b8d36cbf622698018323baf51c64ec43"),
    "final": bytes.fromhex("e739a8f94e26d1356760679cbed643f1c4ce69d10f759cbbd5e6a22bd8f40512"),
}


def _suite_seed(role: str, topology: str, sample_index: int) -> int:
    material = f"{topology}:{sample_index}".encode("ascii")
    digest = hashlib.blake2b(
        material,
        digest_size=8,
        key=_PRIVATE_SUITE_KEYS[role],
        person=b"tegap-v3",
    ).digest()
    return int.from_bytes(digest, "big")


# Iterative submissions use the agent suite; the final verifier switches roles
# and evaluates once on a disjoint held-out suite. Seed keys stay judge-private.
CASE_SPECS_BY_ROLE = {
    role: tuple(
        (topology, _suite_seed(role, topology, sample_index))
        for topology in ("swan", "abilene", "b4")
        for sample_index in range(CASES_PER_TOPOLOGY)
    )
    for role in ("agent", "final")
}


def _node_count(edges: Iterable[tuple[int, int]]) -> int:
    return 1 + max(max(source, target) for source, target in edges)


def _k_shortest_paths(
    node_count: int,
    edge_pairs: tuple[tuple[int, int], ...],
    source: int,
    target: int,
    limit: int,
) -> list[list[int]]:
    adjacency: list[list[tuple[int, int]]] = [[] for _ in range(node_count)]
    for edge_index, (tail, head) in enumerate(edge_pairs):
        adjacency[tail].append((head, edge_index))
    for outgoing in adjacency:
        outgoing.sort()
    heap: list[tuple[int, tuple[int, ...], tuple[int, ...]]] = [(0, (source,), ())]
    answer: list[list[int]] = []
    while heap and len(answer) < limit:
        hops, nodes, path_edges = heapq.heappop(heap)
        current = nodes[-1]
        if current == target:
            answer.append(list(path_edges))
            continue
        if hops >= node_count - 1:
            continue
        for next_node, edge_index in adjacency[current]:
            if next_node in nodes:
                continue
            heapq.heappush(
                heap,
                (hops + 1, nodes + (next_node,), path_edges + (edge_index,)),
            )
    return answer


def _build_instance(topology: str, seed: int, role: str) -> dict[str, Any]:
    rng = random.Random(seed)
    skeleton = TOPOLOGY_EDGES[topology]
    node_count = _node_count(skeleton)
    capacities = [float(24 + rng.randrange(13)) for _ in skeleton]

    nodes = list(range(node_count))
    rng.shuffle(nodes)
    halves = {
        node: int(index >= (node_count + 1) // 2)
        for index, node in enumerate(nodes)
    }
    by_category: dict[tuple[int, int], list[tuple[int, int, list[list[int]]]]] = {
        category: [] for category in itertools.product(range(2), repeat=2)
    }
    for source in range(node_count):
        for target in range(node_count):
            if source == target:
                continue
            paths = _k_shortest_paths(node_count, skeleton, source, target, PATH_LIMIT)
            if paths:
                by_category[(halves[source], halves[target])].append((source, target, paths))

    category_order = list(by_category)
    rng.shuffle(category_order)
    block_allocations = [2, 2, 2, 3]
    selected: list[tuple[int, int, list[list[int]], int]] = []
    search_blocks: list[list[int]] = []
    for category, block_count in zip(category_order, block_allocations):
        candidates = by_category[category]
        tie = {(source, target): rng.random() for source, target, _ in candidates}
        candidates.sort(key=lambda item: (-len(item[2][0]), tie[(item[0], item[1])], item[0], item[1]))
        needed = 3 * block_count
        if len(candidates) < needed:
            raise RuntimeError("generated search category is too small")
        for block_offset in range(block_count):
            block: list[int] = []
            for source, target, paths in candidates[3 * block_offset:3 * (block_offset + 1)]:
                pair_index = len(selected)
                selected.append((source, target, paths, rng.randrange(POP_PARTITIONS)))
                block.append(pair_index)
            search_blocks.append(block)

    rng.shuffle(search_blocks)
    edges = [
        {"source": source, "target": target, "capacity": capacity}
        for (source, target), capacity in zip(skeleton, capacities)
    ]
    pairs = [
        {
            "source": source,
            "target": target,
            "partition": partition,
            "paths": paths,
        }
        for source, target, paths, partition in selected
    ]
    return {
        "id": hashlib.sha256(
            f"tegap-v{SUITE_REVISION}:{role}:{topology}:{seed}".encode("ascii")
        ).hexdigest()[:16],
        "node_count": node_count,
        "edges": edges,
        "pairs": pairs,
        "levels": list(LEVELS),
        "density_limit": DENSITY_LIMIT,
        "pinning_threshold": PINNING_THRESHOLD,
        "pop_partitions": POP_PARTITIONS,
        "query_budget": QUERY_BUDGET,
        "search_blocks": search_blocks,
    }


def _suite(role: str = "agent") -> list[dict[str, Any]]:
    if role not in CASE_SPECS_BY_ROLE:
        raise ValueError("invalid evaluation role")
    instances = [
        _build_instance(topology, seed, role)
        for topology, seed in CASE_SPECS_BY_ROLE[role]
    ]
    for instance in instances:
        _validate_instance(instance)
    return instances


def _validate_instance(instance: dict[str, Any]) -> None:
    if len(instance["pairs"]) != 27 or len(instance["search_blocks"]) != 9:
        raise RuntimeError("bad generated search dimensions")
    flattened = [index for block in instance["search_blocks"] for index in block]
    if sorted(flattened) != list(range(27)) or any(len(block) != 3 for block in instance["search_blocks"]):
        raise RuntimeError("bad generated search blocks")
    edge_count = len(instance["edges"])
    for pair in instance["pairs"]:
        if not pair["paths"] or len(pair["paths"]) > PATH_LIMIT:
            raise RuntimeError("bad generated path catalog")
        for path in pair["paths"]:
            if not path or any(index < 0 or index >= edge_count for index in path):
                raise RuntimeError("bad generated path")


def _normalize_levels(instance: dict[str, Any], answer: Any) -> tuple[int, ...]:
    if isinstance(answer, dict) and set(answer) == {"levels"}:
        answer = answer["levels"]
    if not isinstance(answer, (list, tuple)) or len(answer) != len(instance["pairs"]):
        raise ValueError("wrong demand vector length")
    normalized: list[int] = []
    nonzero = 0
    for value in answer:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("demand levels must be integer indices")
        if value < 0 or value >= len(instance["levels"]):
            raise ValueError("demand level index outside range")
        normalized.append(value)
        if instance["levels"][value] > 0.0:
            nonzero += 1
    if nonzero > instance["density_limit"]:
        raise ValueError("demand density limit exceeded")
    _check_pinned_feasibility(instance, normalized)
    return tuple(normalized)


def _check_pinned_feasibility(instance: dict[str, Any], levels: Iterable[int]) -> None:
    pinned_load = [0.0] * len(instance["edges"])
    for pair, level_index in zip(instance["pairs"], levels):
        demand = float(instance["levels"][level_index])
        if 0.0 < demand <= float(instance["pinning_threshold"]) + FLOW_TOLERANCE:
            for edge_index in pair["paths"][0]:
                pinned_load[edge_index] += demand
    for edge_index, load in enumerate(pinned_load):
        if load > float(instance["edges"][edge_index]["capacity"]) + FLOW_TOLERANCE:
            raise ValueError("pinned shortest-path load exceeds capacity")


def _solve_path_flow(
    instance: dict[str, Any],
    demands: list[float],
    selected_pairs: Iterable[int],
    capacity_scale: float = 1.0,
    capacity_override: list[float] | None = None,
) -> float:
    import numpy as np
    from scipy.optimize import linprog

    records: list[tuple[int, list[int]]] = []
    for pair_index in selected_pairs:
        if demands[pair_index] <= 0.0:
            continue
        records.extend((pair_index, path) for path in instance["pairs"][pair_index]["paths"])
    if not records:
        return 0.0
    row_count = len(instance["edges"]) + len(instance["pairs"])
    matrix = np.zeros((row_count, len(records)), dtype=float)
    for column, (pair_index, path) in enumerate(records):
        for edge_index in path:
            matrix[edge_index, column] += 1.0
        matrix[len(instance["edges"]) + pair_index, column] = 1.0
    if capacity_override is None:
        upper = [float(edge["capacity"]) * capacity_scale for edge in instance["edges"]]
    else:
        upper = [max(0.0, value) for value in capacity_override]
    upper.extend(demands)
    result = linprog(
        -np.ones(len(records), dtype=float),
        A_ub=matrix,
        b_ub=np.asarray(upper, dtype=float),
        bounds=(0.0, None),
        method="highs",
        options={"presolve": True},
    )
    if not result.success or not math.isfinite(float(result.fun)):
        raise RuntimeError("judge flow replay failed")
    return float(-result.fun)


def _evaluate_matrix(instance: dict[str, Any], answer: Any) -> tuple[float, float, float, float]:
    level_indices = _normalize_levels(instance, answer)
    demands = [float(instance["levels"][index]) for index in level_indices]
    pair_indices = list(range(len(demands)))
    optimal = _solve_path_flow(instance, demands, pair_indices)
    pop = 0.0
    for partition in range(instance["pop_partitions"]):
        selected = [
            index for index, pair in enumerate(instance["pairs"])
            if pair["partition"] == partition
        ]
        pop += _solve_path_flow(
            instance,
            demands,
            selected,
            capacity_scale=1.0 / instance["pop_partitions"],
        )

    remaining = [float(edge["capacity"]) for edge in instance["edges"]]
    pinned = 0.0
    large: list[int] = []
    for index, (pair, demand) in enumerate(zip(instance["pairs"], demands)):
        if demand <= 0.0:
            continue
        if demand <= instance["pinning_threshold"] + FLOW_TOLERANCE:
            pinned += demand
            for edge_index in pair["paths"][0]:
                remaining[edge_index] -= demand
        else:
            large.append(index)
    if min(remaining, default=0.0) < -FLOW_TOLERANCE:
        raise ValueError("pinned shortest-path load exceeds capacity")
    pinning = pinned + _solve_path_flow(
        instance,
        demands,
        large,
        capacity_override=remaining,
    )
    gap = max(0.0, optimal - max(pop, pinning))
    return gap, optimal, pop, pinning


class _BudgetOracle:
    def __init__(self, instance: dict[str, Any]):
        self.instance = instance
        self.queries = 0
        self.budget = int(instance["query_budget"])

    def __call__(self, levels: Any) -> tuple[float, float, float, float]:
        if self.queries >= self.budget:
            raise ValueError("oracle query budget exceeded")
        result = _evaluate_matrix(self.instance, levels)
        self.queries += 1
        return result


def _clustered_reference_search(
    instance: dict[str, Any],
    evaluate_gap: Callable[[Any], tuple[float, float, float, float]],
) -> list[int]:
    """MetaOpt clustering V2 pattern: initialize, then optimize and fix blocks."""
    current: list[int] | None = None
    current_gap = -1.0
    for trial in range(10):
        seed = int.from_bytes(
            hashlib.sha256(
                (f"paper-init:{trial}:" + instance["id"]).encode("ascii")
            ).digest()[:8],
            "big",
        )
        rng = random.Random(seed)
        candidate = [0] * len(instance["pairs"])
        for pair_index in rng.sample(range(len(candidate)), instance["density_limit"]):
            candidate[pair_index] = rng.randrange(1, len(instance["levels"]))
        try:
            gap = evaluate_gap(candidate)[0]
        except ValueError:
            continue
        if gap > current_gap:
            current_gap = gap
            current = candidate
    if current is None:
        current = [0] * len(instance["pairs"])
    for block in instance["search_blocks"]:
        best_levels: list[int] | None = None
        best_gap = -1.0
        for values in itertools.product(range(len(instance["levels"])), repeat=len(block)):
            candidate = current.copy()
            for pair_index, value in zip(block, values):
                candidate[pair_index] = value
            try:
                gap = evaluate_gap(candidate)[0]
            except ValueError:
                continue
            if gap > best_gap + 1e-9 or (
                abs(gap - best_gap) <= 1e-9
                and (best_levels is None or tuple(candidate) < tuple(best_levels))
            ):
                best_gap = gap
                best_levels = candidate
        if best_levels is None:
            raise RuntimeError("reference block has no feasible assignment")
        current = best_levels
    return current


class _JointReferenceModel:
    """Small MILP builder for MetaOpt's joint primal-dual rewrite."""

    def __init__(self) -> None:
        self.cost: list[float] = []
        self.lower: list[float] = []
        self.upper: list[float] = []
        self.integrality: list[int] = []
        self.rows: list[dict[int, float]] = []
        self.row_lower: list[float] = []
        self.row_upper: list[float] = []

    def variable(
        self,
        *,
        lower: float = 0.0,
        upper: float = math.inf,
        integer: bool = False,
        cost: float = 0.0,
    ) -> int:
        index = len(self.cost)
        self.cost.append(cost)
        self.lower.append(lower)
        self.upper.append(upper)
        self.integrality.append(1 if integer else 0)
        return index

    def constraint(
        self,
        coefficients: dict[int, float],
        *,
        lower: float = -math.inf,
        upper: float = math.inf,
    ) -> None:
        self.rows.append({index: value for index, value in coefficients.items() if value})
        self.row_lower.append(lower)
        self.row_upper.append(upper)

    def product(self, binary: int, continuous: int) -> int:
        product = self.variable(upper=1.0)
        self.constraint({product: 1.0, binary: -1.0}, upper=0.0)
        self.constraint({product: 1.0, continuous: -1.0}, upper=0.0)
        self.constraint({product: 1.0, binary: -1.0, continuous: -1.0}, lower=-1.0)
        return product

    def solve(self) -> list[float]:
        import gurobipy as gp

        expanded_constraint_count = sum(
            1 if math.isfinite(lower) and math.isfinite(upper) and lower == upper
            else int(math.isfinite(lower)) + int(math.isfinite(upper))
            for lower, upper in zip(self.row_lower, self.row_upper)
        )
        if len(self.cost) > 2_000 or expanded_constraint_count > 2_000:
            raise RuntimeError("global reference exceeds the packaged solver size limit")
        solver = gp.Model("metaopt_global_reference")
        solver.Params.OutputFlag = 0
        solver.Params.TimeLimit = REFERENCE_TIME_LIMIT_SECONDS
        solver.Params.WorkLimit = REFERENCE_WORK_LIMIT
        solver.Params.Threads = REFERENCE_THREADS
        solver.Params.Seed = 0
        solver.Params.MIPGap = 0.0
        variables = []
        for index in range(len(self.cost)):
            upper = gp.GRB.INFINITY if math.isinf(self.upper[index]) else self.upper[index]
            variable_type = gp.GRB.BINARY if self.integrality[index] else gp.GRB.CONTINUOUS
            variables.append(
                solver.addVar(
                    name=f"x_{index}",
                    vtype=variable_type,
                    lb=self.lower[index],
                    ub=upper,
                )
            )
        for row, lower, upper in zip(self.rows, self.row_lower, self.row_upper):
            expression = gp.quicksum(value * variables[index] for index, value in row.items())
            if math.isfinite(lower) and math.isfinite(upper) and lower == upper:
                solver.addConstr(expression == lower)
            else:
                if math.isfinite(lower):
                    solver.addConstr(expression >= lower)
                if math.isfinite(upper):
                    solver.addConstr(expression <= upper)
        solver.setObjective(
            gp.quicksum(value * variables[index] for index, value in enumerate(self.cost) if value),
            gp.GRB.MINIMIZE,
        )
        solver.optimize()
        if solver.SolCount < 1:
            raise RuntimeError("global MetaOpt reference found no incumbent")
        solution = [float(variable.X) for variable in variables]
        if not all(math.isfinite(value) for value in solution):
            raise RuntimeError("global MetaOpt reference returned a non-finite incumbent")
        return solution


def _add_linear_expression(
    target: dict[int, float],
    source: dict[int, float],
    scale: float = 1.0,
) -> None:
    for index, value in source.items():
        target[index] = target.get(index, 0.0) + scale * value


def _joint_reference_search(instance: dict[str, Any]) -> list[int]:
    model = _JointReferenceModel()
    pair_count = len(instance["pairs"])
    edge_count = len(instance["edges"])
    small = [model.variable(upper=1.0, integer=True) for _ in range(pair_count)]
    large = [model.variable(upper=1.0, integer=True) for _ in range(pair_count)]
    for pair_index in range(pair_count):
        model.constraint({small[pair_index]: 1.0, large[pair_index]: 1.0}, upper=1.0)
    model.constraint(
        {index: 1.0 for index in small + large},
        upper=float(instance["density_limit"]),
    )
    for edge_index, edge in enumerate(instance["edges"]):
        pinned = {
            small[pair_index]: 6.0
            for pair_index, pair in enumerate(instance["pairs"])
            if edge_index in pair["paths"][0]
        }
        model.constraint(pinned, upper=float(edge["capacity"]))

    optimal_flows: list[list[int]] = []
    for pair_index, pair in enumerate(instance["pairs"]):
        flows = [model.variable(upper=18.0, cost=-1.0) for _ in pair["paths"]]
        optimal_flows.append(flows)
        bound = {flow: 1.0 for flow in flows}
        bound[small[pair_index]] = -6.0
        bound[large[pair_index]] = -18.0
        model.constraint(bound, upper=0.0)
    for edge_index, edge in enumerate(instance["edges"]):
        load: dict[int, float] = {}
        for pair_index, pair in enumerate(instance["pairs"]):
            for path_index, path in enumerate(pair["paths"]):
                if edge_index in path:
                    load[optimal_flows[pair_index][path_index]] = 1.0
        model.constraint(load, upper=float(edge["capacity"]))

    combined = model.variable(upper=18.0 * float(instance["density_limit"]), cost=1.0)
    pop_dual_expression: dict[int, float] = {}
    pop_primal_expression: dict[int, float] = {}
    for partition in range(int(instance["pop_partitions"])):
        edge_dual = [model.variable(upper=1.0) for _ in range(edge_count)]
        partition_flows: dict[tuple[int, int], int] = {}
        for edge_index, edge in enumerate(instance["edges"]):
            pop_dual_expression[edge_dual[edge_index]] = (
                pop_dual_expression.get(edge_dual[edge_index], 0.0)
                + float(edge["capacity"]) / float(instance["pop_partitions"])
            )
        for pair_index, pair in enumerate(instance["pairs"]):
            if int(pair["partition"]) != partition:
                continue
            flows = []
            for path_index, _path in enumerate(pair["paths"]):
                flow = model.variable(upper=18.0)
                flows.append(flow)
                partition_flows[(pair_index, path_index)] = flow
                pop_primal_expression[flow] = 1.0
            demand_bound = {flow: 1.0 for flow in flows}
            demand_bound[small[pair_index]] = -6.0
            demand_bound[large[pair_index]] = -18.0
            model.constraint(demand_bound, upper=0.0)
            demand_dual = model.variable(upper=1.0)
            for path in pair["paths"]:
                dual_bound = {demand_dual: 1.0}
                for edge_index in path:
                    dual_bound[edge_dual[edge_index]] = dual_bound.get(edge_dual[edge_index], 0.0) + 1.0
                model.constraint(dual_bound, lower=1.0)
            small_product = model.product(small[pair_index], demand_dual)
            large_product = model.product(large[pair_index], demand_dual)
            pop_dual_expression[small_product] = pop_dual_expression.get(small_product, 0.0) + 6.0
            pop_dual_expression[large_product] = pop_dual_expression.get(large_product, 0.0) + 18.0
        for edge_index, edge in enumerate(instance["edges"]):
            edge_load: dict[int, float] = {}
            for pair_index, pair in enumerate(instance["pairs"]):
                if int(pair["partition"]) != partition:
                    continue
                for path_index, path in enumerate(pair["paths"]):
                    if edge_index in path:
                        edge_load[partition_flows[(pair_index, path_index)]] = 1.0
            model.constraint(
                edge_load,
                upper=float(edge["capacity"]) / float(instance["pop_partitions"]),
            )
    pop_strong_duality = dict(pop_primal_expression)
    _add_linear_expression(pop_strong_duality, pop_dual_expression, -1.0)
    model.constraint(pop_strong_duality, lower=0.0, upper=0.0)
    pop_bound = {combined: 1.0}
    _add_linear_expression(pop_bound, pop_dual_expression, -1.0)
    model.constraint(pop_bound, lower=0.0)

    dp_dual_expression: dict[int, float] = {index: 6.0 for index in small}
    dp_primal_expression: dict[int, float] = {index: 6.0 for index in small}
    dp_flows: list[list[int]] = []
    for pair_index, pair in enumerate(instance["pairs"]):
        flows = [model.variable(upper=18.0) for _ in pair["paths"]]
        dp_flows.append(flows)
        for flow in flows:
            dp_primal_expression[flow] = 1.0
        demand_bound = {flow: 1.0 for flow in flows}
        demand_bound[large[pair_index]] = -18.0
        model.constraint(demand_bound, upper=0.0)
    for edge_index, edge in enumerate(instance["edges"]):
        edge_load: dict[int, float] = {}
        for pair_index, pair in enumerate(instance["pairs"]):
            if edge_index in pair["paths"][0]:
                edge_load[small[pair_index]] = edge_load.get(small[pair_index], 0.0) + 6.0
            for path_index, path in enumerate(pair["paths"]):
                if edge_index in path:
                    edge_load[dp_flows[pair_index][path_index]] = 1.0
        model.constraint(edge_load, upper=float(edge["capacity"]))
    dp_edge_dual = [model.variable(upper=1.0) for _ in range(edge_count)]
    for edge_index, edge in enumerate(instance["edges"]):
        dual = dp_edge_dual[edge_index]
        dp_dual_expression[dual] = dp_dual_expression.get(dual, 0.0) + float(edge["capacity"])
        for pair_index, pair in enumerate(instance["pairs"]):
            if edge_index in pair["paths"][0]:
                product = model.product(small[pair_index], dual)
                dp_dual_expression[product] = dp_dual_expression.get(product, 0.0) - 6.0
    for pair_index, pair in enumerate(instance["pairs"]):
        demand_dual = model.variable(upper=1.0)
        for path in pair["paths"]:
            dual_bound = {demand_dual: 1.0, large[pair_index]: -1.0}
            for edge_index in path:
                dual_bound[dp_edge_dual[edge_index]] = dual_bound.get(dp_edge_dual[edge_index], 0.0) + 1.0
            model.constraint(dual_bound, lower=0.0)
        product = model.product(large[pair_index], demand_dual)
        dp_dual_expression[product] = dp_dual_expression.get(product, 0.0) + 18.0
    dp_strong_duality = dict(dp_primal_expression)
    _add_linear_expression(dp_strong_duality, dp_dual_expression, -1.0)
    model.constraint(dp_strong_duality, lower=0.0, upper=0.0)
    dp_bound = {combined: 1.0}
    _add_linear_expression(dp_bound, dp_dual_expression, -1.0)
    model.constraint(dp_bound, lower=0.0)

    solution = model.solve()
    return [
        2 if solution[large[index]] >= 0.5 else 1 if solution[small[index]] >= 0.5 else 0
        for index in range(pair_count)
    ]


def _reference_search(
    instance: dict[str, Any],
    evaluate_gap: Callable[[Any], tuple[float, float, float, float]],
) -> list[int]:
    answer = _joint_reference_search(instance)
    evaluate_gap(answer)
    return answer


def _load_local_strategy(path: Path) -> Callable[[dict[str, Any], Callable[..., Any]], Any]:
    if path.stat().st_size > 64_000:
        raise ValueError("unsupported submission artifact")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    strategy_name = APPROVED_STRATEGY_HASHES.get(digest)
    if strategy_name is None:
        raise ValueError("unsupported submission artifact")
    specification = importlib.util.spec_from_file_location(f"tegap_{strategy_name}", path)
    if specification is None or specification.loader is None:
        raise ValueError("could not load local strategy")
    module = importlib.util.module_from_spec(specification)
    reviewer_directory = str(Path(__file__).resolve().parent)
    inserted = reviewer_directory not in sys.path
    if inserted:
        sys.path.insert(0, reviewer_directory)
    try:
        specification.loader.exec_module(module)
    finally:
        if inserted:
            sys.path.remove(reviewer_directory)
    strategy = getattr(module, "search", None)
    if not callable(strategy):
        raise ValueError("local strategy has no search function")
    return strategy


def _run_local_strategy(path: Path, instances: list[dict[str, Any]]) -> list[Any]:
    strategy = _load_local_strategy(path)
    answers: list[Any] = []
    for instance in instances:
        oracle = _BudgetOracle(instance)
        answer = strategy(instance, oracle)
        if oracle.queries > instance["query_budget"]:
            raise ValueError("oracle query budget exceeded")
        answers.append(answer)
    return answers


def _is_harbor_runtime_file(relative: Path) -> bool:
    return len(relative.parts) == 1 and relative.name in HARBOR_RUNTIME_FILES


def _locked_tree_hash(source: Path) -> str:
    digest = hashlib.sha256()
    digest.update(LOCKED_TREE_DOMAIN)
    editable = Path("MetaOptimize/TrafficEngineering/BudgetedDemandSearch.cs")
    candidate_root = Path("MetaOptimize/TrafficEngineering/Candidate")
    paths: list[tuple[str, Path]] = []
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        if any(part in {".git", "bin", "obj", "__pycache__"} for part in relative.parts):
            continue
        if (
            not path.is_file()
            or relative == editable
            or candidate_root in relative.parents
            or _is_harbor_runtime_file(relative)
        ):
            continue
        paths.append((relative.as_posix(), path))
    for relative, path in sorted(paths):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(131_072), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def _validate_project(source: Path) -> None:
    if not source.is_dir():
        raise ValueError("submission is not a directory")
    total_bytes = 0
    file_count = 0
    editable = Path("MetaOptimize/TrafficEngineering/BudgetedDemandSearch.cs")
    candidate_root = Path("MetaOptimize/TrafficEngineering/Candidate")
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        if any(part in {".git", "bin", "obj", "__pycache__"} for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError("symlinks are not allowed")
        if not path.is_file():
            continue
        file_count += 1
        total_bytes += path.stat().st_size
        if file_count > MAX_FILES or total_bytes > MAX_SUBMISSION_BYTES:
            raise ValueError("submission exceeds size limits")
        if relative == editable:
            continue
        if candidate_root in relative.parents:
            if path.suffix != ".cs":
                raise ValueError("candidate helper files must be C# source")
            continue
    if not (source / editable).is_file():
        raise ValueError("missing BudgetedDemandSearch.cs")
    if _locked_tree_hash(source) != LOCKED_TREE_HASH:
        raise ValueError("locked substrate file changed")


def _copy_project(source: Path, destination: Path) -> None:
    source_root = source.resolve()

    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored = {name for name in names if name in {".git", "bin", "obj", "__pycache__"}}
        if Path(directory).resolve() == source_root:
            ignored.update(name for name in names if name in HARBOR_RUNTIME_FILES)
        return ignored
    shutil.copytree(source, destination, ignore=ignore)


def _child_limits() -> None:
    resource.setrlimit(
        resource.RLIMIT_CPU,
        (CASE_CPU_LIMIT_SECONDS, CASE_CPU_LIMIT_SECONDS + 2),
    )
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(
        resource.RLIMIT_NOFILE,
        (MAX_CHILD_FILE_DESCRIPTORS, MAX_CHILD_FILE_DESCRIPTORS),
    )
    resource.setrlimit(
        resource.RLIMIT_NPROC,
        (MAX_CHILD_PROCESSES, MAX_CHILD_PROCESSES),
    )
    if os.geteuid() == 0:
        os.setgroups([])
        os.setgid(65534)
        os.setuid(65534)


def _harden_judge_directory() -> None:
    """Keep private suite material unreadable by the unprivileged C# child."""
    evaluator_directory = Path(__file__).resolve().parent
    if evaluator_directory == Path("/judge"):
        evaluator_directory.chmod(0o700)


def _run_csharp_project(source: Path, instances: list[dict[str, Any]]) -> list[Any]:
    if shutil.which("dotnet") is None:
        raise ValueError("dotnet SDK is unavailable")
    _validate_project(source)
    with tempfile.TemporaryDirectory(prefix="tegap_eval_") as temporary:
        root = Path(temporary)
        app = root / "app"
        _copy_project(source, app)
        environment = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "DOTNET_CLI_HOME": str(root / "dotnet_home"),
            "NUGET_PACKAGES": str(root / "nuget_packages"),
            "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
            "DOTNET_NOLOGO": "1",
            "NUGET_XMLDOC_MODE": "skip",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
        }
        (root / "dotnet_home").mkdir()
        build = subprocess.run(
            [
                "dotnet", "build", "MetaOptimize.Challenge/MetaOptimize.Challenge.csproj",
                "-c", "Release", "--nologo", "-v", "quiet",
            ],
            cwd=app,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=BUILD_TIMEOUT_SECONDS,
            check=False,
        )
        if build.returncode != 0:
            raise ValueError("submission does not build")
        assembly = app / "MetaOptimize.Challenge/bin/Release/net8.0/MetaOptimize.Challenge.dll"
        if not assembly.is_file():
            raise ValueError("challenge build produced no executable")

        # tempfile roots are 0700. Permit the deliberately unprivileged runtime
        # to traverse only its copied project and already-built outputs.
        root.chmod(0o755)
        (root / "dotnet_home").chmod(0o755)

        answers: list[Any] = []
        for instance in instances:
            output_path = root / f"output_{len(answers)}.json"
            with output_path.open("wb") as output:
                process = subprocess.Popen(
                    ["dotnet", str(assembly)],
                    cwd=app,
                    env=environment,
                    stdin=subprocess.PIPE,
                    stdout=output,
                    stderr=subprocess.DEVNULL,
                    text=False,
                    start_new_session=True,
                    preexec_fn=_child_limits,
                )
                assert process.stdin is not None
                process.stdin.write(
                    json.dumps(instance, separators=(",", ":"), allow_nan=False).encode("utf-8")
                )
                process.stdin.close()
                deadline = time.monotonic() + CASE_TIMEOUT_SECONDS + 3
                while process.poll() is None:
                    if output_path.stat().st_size > MAX_OUTPUT_BYTES:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                        raise ValueError("search output too large")
                    if time.monotonic() >= deadline:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                        raise ValueError("search timed out on an instance")
                    time.sleep(0.02)
            # A submission may leave helpers alive after its entry point exits.
            # Kill the process group before starting the next private instance.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            if process.returncode != 0:
                raise ValueError("search failed on an instance")
            if output_path.stat().st_size > MAX_OUTPUT_BYTES:
                raise ValueError("search output too large")
            try:
                result = json.loads(output_path.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise ValueError("search returned invalid JSON") from None
            if not isinstance(result, dict) or set(result) != {"levels", "queries"}:
                raise ValueError("search returned invalid result")
            queries = result["queries"]
            if isinstance(queries, bool) or not isinstance(queries, int) or not 0 <= queries <= QUERY_BUDGET:
                raise ValueError("search returned invalid query count")
            answers.append(result["levels"])
        return answers


def _reference_answers(instances: list[dict[str, Any]]) -> list[list[int]]:
    answers: list[list[int]] = []
    for instance in instances:
        oracle = _BudgetOracle(instance)
        answer = _reference_search(instance, oracle)
        if oracle.queries > QUERY_BUDGET:
            raise RuntimeError("reference exceeded query budget")
        answers.append(answer)
    return answers


def _score_answers_detailed(
    instances: list[dict[str, Any]],
    answers: list[Any],
) -> tuple[float, float, list[float]]:
    if len(answers) != len(instances):
        raise ValueError("wrong answer count")
    gaps = [_evaluate_matrix(instance, answer)[0] for instance, answer in zip(instances, answers)]
    mean_gap = sum(gaps) / len(gaps)
    score = 100.0 * (1.0 - math.exp(-mean_gap / SCORE_SCALE))
    return min(100.0, max(0.0, score)), mean_gap, gaps


def _score_answers(instances: list[dict[str, Any]], answers: list[Any]) -> tuple[float, float]:
    score, mean_gap, _gaps = _score_answers_detailed(instances, answers)
    return score, mean_gap


def _gap_diagnostics(role: str, gaps: list[float]) -> dict[str, Any]:
    topology_gaps: dict[str, list[float]] = {"swan": [], "abilene": [], "b4": []}
    for (topology, _seed), gap in zip(CASE_SPECS_BY_ROLE[role], gaps):
        topology_gaps[topology].append(gap)
    total = sum(gaps)
    return {
        "per_case_gaps": list(gaps),
        "per_topology_mean": {
            topology: sum(values) / len(values)
            for topology, values in topology_gaps.items()
        },
        "largest_case_share": max(gaps, default=0.0) / total if total > 0.0 else 0.0,
    }


def _load_reference_cache() -> None:
    if _REFERENCE_DATA or REFERENCE_CACHE_PATH is None or not REFERENCE_CACHE_PATH.is_file():
        return
    try:
        payload = json.loads(REFERENCE_CACHE_PATH.read_text(encoding="utf-8"))
        if payload.get("tag") != REFERENCE_CACHE_TAG or not isinstance(payload.get("roles"), dict):
            return
        for role in ("agent", "final"):
            data = payload["roles"].get(role)
            if isinstance(data, dict) and isinstance(data.get("score"), (int, float)):
                _REFERENCE_DATA[role] = data
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return


def _write_reference_cache() -> None:
    if REFERENCE_CACHE_PATH is None:
        return
    temporary = REFERENCE_CACHE_PATH.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"tag": REFERENCE_CACHE_TAG, "roles": _REFERENCE_DATA}, separators=(",", ":")),
        encoding="utf-8",
    )
    os.replace(temporary, REFERENCE_CACHE_PATH)


def _reference_data(role: str, instances: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    _load_reference_cache()
    if role in _REFERENCE_DATA:
        return _REFERENCE_DATA[role]
    if instances is None:
        instances = _suite(role)
    answers = _reference_answers(instances)
    score, mean_gap, gaps = _score_answers_detailed(instances, answers)
    data = {
        "score": score,
        "mean_gap": mean_gap,
        "diagnostics": _gap_diagnostics(role, gaps),
    }
    _REFERENCE_DATA[role] = data
    try:
        _write_reference_cache()
    except OSError:
        pass
    return data


def internal_diagnostics() -> dict[str, Any]:
    """Reviewer-only balance diagnostics; never returned by the evaluation API."""
    return {
        "reference": {
            role: data.get("diagnostics", {})
            for role, data in _REFERENCE_DATA.items()
        },
        "last_candidate": dict(_LAST_INTERNAL_DIAGNOSTICS),
    }


def _evaluation_role() -> str:
    role = os.environ.get("FRONTIER_SUBMISSION_ROLE", "agent")
    if role not in {"agent", "final"}:
        raise ValueError("invalid submission role")
    return role


def prepare() -> dict[str, Any]:
    _harden_judge_directory()
    # Iterative evaluation uses forked children, which inherit this in-memory
    # development reference. The final reference is intentionally computed
    # only after the submitted program has finished on the held-out suite.
    _reference_data("agent")
    return {
        "suite_revision": SUITE_REVISION,
        "instance_count": len(CASE_SPECS_BY_ROLE["agent"]),
        "final_instance_count": len(CASE_SPECS_BY_ROLE["final"]),
        "query_budget": QUERY_BUDGET,
    }


def evaluate(solution_path: str) -> tuple[float, float, str, dict[str, Any]]:
    """Evaluate a C# search project or one of the private local calibration strategies."""
    try:
        role = _evaluation_role()
        instances = _suite(role)
        path = Path(solution_path).resolve()
        if not path.exists():
            raise ValueError("submission path does not exist")
        if path.is_file() and path.suffix == ".py":
            answers = _run_local_strategy(path, instances)
        elif path.is_dir():
            answers = _run_csharp_project(path, instances)
        else:
            raise ValueError("unsupported submission artifact")

        reference = _reference_data(role, instances)
        reference_score = float(reference["score"])
        candidate_score, mean_gap, candidate_gaps = _score_answers_detailed(instances, answers)
        global _LAST_INTERNAL_DIAGNOSTICS
        _LAST_INTERNAL_DIAGNOSTICS = {
            "role": role,
            **_gap_diagnostics(role, candidate_gaps),
        }
        margin = candidate_score - reference_score
        metrics = {
            "beats_reference": 1 if candidate_score >= reference_score else 0,
            "reference_score": reference_score,
            "margin": margin,
            "mean_gap": mean_gap,
            "instance_count": len(instances),
        }
        message = (
            f"score={candidate_score:.6f}; mean_gap={mean_gap:.6f}; "
            f"beats_reference={metrics['beats_reference']}"
        )
        return candidate_score, mean_gap, message, metrics
    except Exception as exc:
        if isinstance(exc, ValueError):
            reason = str(exc)[:120] or "invalid submission"
        else:
            reason = "evaluation failed"
        return 0.0, 0.0, reason, {}


def _main() -> int:
    solution = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).with_name("reference.py"))
    score, unbounded, message, metrics = evaluate(solution)
    print(json.dumps({
        "score": score,
        "score_unbounded": unbounded,
        "message": message,
        "metrics": metrics,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
