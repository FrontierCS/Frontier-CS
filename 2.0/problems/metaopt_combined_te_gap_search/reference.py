"""Anytime joint MetaOpt primal-dual reference for local evaluation."""
from __future__ import annotations

import math
from typing import Any, Callable

GLOBAL_TIME_LIMIT_SECONDS = 10.0
GLOBAL_WORK_LIMIT = 6.0
GLOBAL_THREADS = 4


class _Model:
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
        """Exact product for a binary and a continuous variable in [0,1]."""
        product = self.variable(upper=1.0)
        self.constraint({product: 1.0, binary: -1.0}, upper=0.0)
        self.constraint({product: 1.0, continuous: -1.0}, upper=0.0)
        self.constraint({product: 1.0, binary: -1.0, continuous: -1.0}, lower=-1.0)
        return product

    def solve(
        self,
        initial: dict[int, float] | None = None,
        *,
        random_seed: int = 0,
    ) -> list[float]:
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
        solver.Params.TimeLimit = GLOBAL_TIME_LIMIT_SECONDS
        solver.Params.WorkLimit = GLOBAL_WORK_LIMIT
        solver.Params.Threads = GLOBAL_THREADS
        solver.Params.Seed = random_seed
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
        if initial:
            for index, value in initial.items():
                variables[index].Start = value
        solver.optimize()
        if solver.SolCount < 1:
            raise RuntimeError("global MetaOpt reference found no incumbent")
        solution = [float(variable.X) for variable in variables]
        if len(solution) != len(self.cost) or not all(math.isfinite(value) for value in solution):
            raise RuntimeError("global MetaOpt reference found no incumbent")
        return solution


def _add_expression(target: dict[int, float], source: dict[int, float], scale: float = 1.0) -> None:
    for index, value in source.items():
        target[index] = target.get(index, 0.0) + scale * value


def _joint_metaopt(
    instance: dict[str, Any],
    initial: list[int] | None = None,
    *,
    random_seed: int = 0,
) -> list[int]:
    """Joint primal/dual rewrite of OPT minus max(POP, demand pinning)."""
    model = _Model()
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
        coefficients = {flow: 1.0 for flow in flows}
        coefficients[small[pair_index]] = -6.0
        coefficients[large[pair_index]] = -18.0
        model.constraint(coefficients, upper=0.0)
    for edge_index, edge in enumerate(instance["edges"]):
        coefficients: dict[int, float] = {}
        for pair_index, pair in enumerate(instance["pairs"]):
            for path_index, path in enumerate(pair["paths"]):
                if edge_index in path:
                    coefficients[optimal_flows[pair_index][path_index]] = 1.0
        model.constraint(coefficients, upper=float(edge["capacity"]))

    combined = model.variable(upper=18.0 * float(instance["density_limit"]), cost=1.0)

    pop_expression: dict[int, float] = {}
    pop_primal_expression: dict[int, float] = {}
    for partition in range(int(instance["pop_partitions"])):
        edge_dual = [model.variable(upper=1.0) for _ in range(edge_count)]
        partition_flows: dict[tuple[int, int], int] = {}
        for edge_index, edge in enumerate(instance["edges"]):
            pop_expression[edge_dual[edge_index]] = (
                pop_expression.get(edge_dual[edge_index], 0.0)
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
                coefficients = {demand_dual: 1.0}
                for edge_index in path:
                    coefficients[edge_dual[edge_index]] = coefficients.get(edge_dual[edge_index], 0.0) + 1.0
                model.constraint(coefficients, lower=1.0)
            small_product = model.product(small[pair_index], demand_dual)
            large_product = model.product(large[pair_index], demand_dual)
            pop_expression[small_product] = pop_expression.get(small_product, 0.0) + 6.0
            pop_expression[large_product] = pop_expression.get(large_product, 0.0) + 18.0
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
    _add_expression(pop_strong_duality, pop_expression, -1.0)
    model.constraint(pop_strong_duality, lower=0.0, upper=0.0)
    pop_bound = {combined: 1.0}
    _add_expression(pop_bound, pop_expression, -1.0)
    model.constraint(pop_bound, lower=0.0)

    dp_expression: dict[int, float] = {index: 6.0 for index in small}
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
        dp_expression[dual] = dp_expression.get(dual, 0.0) + float(edge["capacity"])
        for pair_index, pair in enumerate(instance["pairs"]):
            if edge_index in pair["paths"][0]:
                capacity_product = model.product(small[pair_index], dual)
                dp_expression[capacity_product] = dp_expression.get(capacity_product, 0.0) - 6.0
    for pair_index, pair in enumerate(instance["pairs"]):
        demand_dual = model.variable(upper=1.0)
        for path in pair["paths"]:
            coefficients = {demand_dual: 1.0, large[pair_index]: -1.0}
            for edge_index in path:
                coefficients[dp_edge_dual[edge_index]] = (
                    coefficients.get(dp_edge_dual[edge_index], 0.0) + 1.0
                )
            model.constraint(coefficients, lower=0.0)
        large_product = model.product(large[pair_index], demand_dual)
        dp_expression[large_product] = dp_expression.get(large_product, 0.0) + 18.0
    dp_strong_duality = dict(dp_primal_expression)
    _add_expression(dp_strong_duality, dp_expression, -1.0)
    model.constraint(dp_strong_duality, lower=0.0, upper=0.0)
    dp_bound = {combined: 1.0}
    _add_expression(dp_bound, dp_expression, -1.0)
    model.constraint(dp_bound, lower=0.0)

    initial_values = None
    if initial is not None:
        initial_values = {}
        for pair_index, level in enumerate(initial):
            initial_values[small[pair_index]] = 1.0 if level == 1 else 0.0
            initial_values[large[pair_index]] = 1.0 if level == 2 else 0.0
    solution = model.solve(initial_values, random_seed=random_seed)
    answer: list[int] = []
    for pair_index in range(pair_count):
        if solution[large[pair_index]] >= 0.5:
            answer.append(2)
        elif solution[small[pair_index]] >= 0.5:
            answer.append(1)
        else:
            answer.append(0)
    return answer


def search(instance: dict[str, Any], evaluate_gap: Callable[[Any], tuple[float, ...]]) -> list[int]:
    answer = _joint_metaopt(instance)
    evaluate_gap(answer)
    return answer
