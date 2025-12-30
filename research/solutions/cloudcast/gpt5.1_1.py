import os
import json
from typing import Dict, List, Any, Tuple

import networkx as nx


class BroadCastTopology:
    def __init__(self, src: str, dsts: List[str], num_partitions: int):
        self.src = src
        self.dsts = dsts
        self.num_partitions = int(num_partitions)
        self.paths: Dict[str, Dict[str, List[List[Any]]]] = {
            dst: {str(i): None for i in range(self.num_partitions)} for dst in dsts
        }

    def append_dst_partition_path(self, dst: str, partition: int, path: List[Any]):
        partition = str(partition)
        if self.paths[dst][partition] is None:
            self.paths[dst][partition] = []
        self.paths[dst][partition].append(path)

    def set_dst_partition_paths(self, dst: str, partition: int, paths: List[List[Any]]):
        partition = str(partition)
        self.paths[dst][partition] = paths

    def set_num_partitions(self, num_partitions: int):
        self.num_partitions = int(num_partitions)


def _compute_candidate_paths(
    src: str,
    dst: str,
    G: nx.DiGraph,
    edge_loads: Dict[Tuple[str, str], int],
    max_paths: int,
) -> List[Dict[str, Any]]:
    candidate_paths: List[Dict[str, Any]] = []

    try:
        path_gen = nx.shortest_simple_paths(G, src, dst, weight="cost")
    except (nx.NetworkXNoPath, nx.NodeNotFound, nx.NetworkXError):
        path_gen = None

    if path_gen is not None:
        try:
            for idx, nodes in enumerate(path_gen):
                if idx >= max_paths:
                    break
                if len(nodes) <= 1:
                    continue

                total_cost = 0.0
                effective_capacity = float("inf")
                edges: List[Tuple[str, str]] = []
                edges_data: List[List[Any]] = []
                path_valid = True

                for u, v in zip(nodes[:-1], nodes[1:]):
                    if u == v or not G.has_edge(u, v):
                        path_valid = False
                        break
                    data = G[u][v]
                    edges.append((u, v))
                    edges_data.append([u, v, data])

                    c = data.get("cost", 0.0)
                    if c < 0:
                        c = 0.0
                    total_cost += c

                    throughput = data.get("throughput", 0.0)
                    if throughput <= 0:
                        effective_capacity = 0.0
                    else:
                        load = edge_loads.get((u, v), 0)
                        adj_throughput = throughput / (1.0 + float(load))
                        if adj_throughput <= 0:
                            effective_capacity = 0.0
                        else:
                            if effective_capacity > adj_throughput:
                                effective_capacity = adj_throughput

                if not path_valid:
                    continue

                cap = max(effective_capacity, 1e-9)
                candidate_paths.append(
                    {
                        "nodes": nodes,
                        "edges": edges,
                        "edges_data": edges_data,
                        "cost": total_cost,
                        "capacity": cap,
                    }
                )
        except nx.NetworkXNoPath:
            pass

    if not candidate_paths:
        try:
            nodes = nx.dijkstra_path(G, src, dst, weight="cost")
        except (nx.NetworkXNoPath, nx.NodeNotFound, nx.NetworkXError):
            return []

        if len(nodes) <= 1:
            return []

        total_cost = 0.0
        effective_capacity = float("inf")
        edges = []
        edges_data = []
        for u, v in zip(nodes[:-1], nodes[1:]):
            data = G[u][v]
            edges.append((u, v))
            edges_data.append([u, v, data])

            c = data.get("cost", 0.0)
            if c < 0:
                c = 0.0
            total_cost += c

            throughput = data.get("throughput", 0.0)
            if throughput <= 0:
                cap = 1e-9
            else:
                cap = throughput
            if effective_capacity > cap:
                effective_capacity = cap

        candidate_paths.append(
            {
                "nodes": nodes,
                "edges": edges,
                "edges_data": edges_data,
                "cost": total_cost,
                "capacity": max(effective_capacity, 1e-9),
            }
        )

    return candidate_paths


def search_algorithm(src: str, dsts: List[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    num_partitions = int(num_partitions)

    if num_partitions <= 0:
        return bc_topology

    edge_loads: Dict[Tuple[str, str], int] = {}

    for dst in dsts:
        if dst == src:
            for pid in range(num_partitions):
                bc_topology.set_dst_partition_paths(dst, pid, [])
            continue

        max_paths = max(1, min(6, num_partitions))
        candidate_paths = _compute_candidate_paths(src, dst, G, edge_loads, max_paths)

        if not candidate_paths:
            for pid in range(num_partitions):
                bc_topology.set_dst_partition_paths(dst, pid, [])
            continue

        P = num_partitions
        K = len(candidate_paths)

        if K == 1 or P <= 1:
            path0 = candidate_paths[0]
            edges_data_0 = path0["edges_data"]
            for pid in range(P):
                bc_topology.set_dst_partition_paths(
                    dst, pid, [[e[0], e[1], e[2]] for e in edges_data_0]
                )
            for (u, v) in path0["edges"]:
                edge_loads[(u, v)] = edge_loads.get((u, v), 0) + P
            continue

        gamma = 1.0
        costs = [max(p["cost"], 1e-9) for p in candidate_paths]
        capacities = [max(p["capacity"], 1e-9) for p in candidate_paths]

        weights: List[float] = []
        for c, cap in zip(costs, capacities):
            w = cap / (c**gamma)
            if w < 0.0:
                w = 0.0
            weights.append(w)

        total_w = sum(weights)
        if not (total_w > 0.0):
            weights = [1.0 for _ in range(K)]
            total_w = float(K)

        raw_alloc = [P * (w / total_w) for w in weights]
        counts = [int(x) for x in raw_alloc]
        assigned = sum(counts)
        remaining = P - assigned

        if remaining > 0:
            fracs = [raw_alloc[i] - float(counts[i]) for i in range(K)]
            order = sorted(
                range(K),
                key=lambda i: (-fracs[i], costs[i], -capacities[i]),
            )
            idx = 0
            while remaining > 0 and idx < K:
                i = order[idx]
                counts[i] += 1
                remaining -= 1
                idx += 1
            idx = 0
            while remaining > 0:
                counts[idx % K] += 1
                remaining -= 1
                idx += 1
        elif remaining < 0:
            over = -remaining
            order = sorted(
                range(K),
                key=lambda i: (-counts[i], capacities[i], costs[i]),
            )
            idx = 0
            while over > 0 and idx < K:
                i = order[idx]
                if counts[i] > 0:
                    counts[i] -= 1
                    over -= 1
                else:
                    idx += 1

        diff = P - sum(counts)
        if diff != 0:
            if diff > 0:
                best = min(range(K), key=lambda i: costs[i])
                counts[best] += diff
            else:
                remove = -diff
                worst = max(range(K), key=lambda i: costs[i])
                dec = min(remove, counts[worst])
                counts[worst] -= dec
                rem = remove - dec
                if rem > 0:
                    best = min(range(K), key=lambda i: costs[i])
                    counts[best] = max(0, counts[best] - rem)

        path_index_for_partition: List[int] = []
        for i, cnt in enumerate(counts):
            if cnt > 0:
                path_index_for_partition.extend([i] * cnt)

        if len(path_index_for_partition) > P:
            path_index_for_partition = path_index_for_partition[:P]
        elif len(path_index_for_partition) < P:
            best = min(range(K), key=lambda i: costs[i])
            path_index_for_partition.extend([best] * (P - len(path_index_for_partition)))

        for pid in range(P):
            idx = path_index_for_partition[pid]
            edges_data = candidate_paths[idx]["edges_data"]
            bc_topology.set_dst_partition_paths(
                dst, pid, [[e[0], e[1], e[2]] for e in edges_data]
            )

        for i, path in enumerate(candidate_paths):
            cnt_i = counts[i]
            if cnt_i <= 0:
                continue
            for (u, v) in path["edges"]:
                edge_loads[(u, v)] = edge_loads.get((u, v), 0) + cnt_i

    return bc_topology


class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        return {"program_path": os.path.abspath(__file__)}