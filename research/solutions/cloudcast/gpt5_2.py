import json
import networkx as nx
from collections import defaultdict
from typing import Dict, Any


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import networkx as nx
from collections import defaultdict

class BroadCastTopology:
    def __init__(self, src: str, dsts: list[str], num_partitions: int):
        self.src = src
        self.dsts = dsts
        self.num_partitions = int(num_partitions)
        self.paths = {dst: {str(i): None for i in range(self.num_partitions)} for dst in dsts}

    def append_dst_partition_path(self, dst: str, partition: int, path: list):
        partition = str(partition)
        if self.paths[dst][partition] is None:
            self.paths[dst][partition] = []
        self.paths[dst][partition].append(path)

    def set_dst_partition_paths(self, dst: str, partition: int, paths: list[list]):
        partition = str(partition)
        self.paths[dst][partition] = paths

    def set_num_partitions(self, num_partitions: int):
        self.num_partitions = num_partitions


def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    """
    Design routing paths for broadcasting data partitions to multiple destinations.

    Heuristic approach:
    - Build per-partition shortest-path trees with dynamic edge weights that combine cost and
      mild congestion penalties based on how many previous partitions used an edge (normalized by throughput).
    - This encourages cost-efficient trees while gently spreading load to avoid severe bottlenecks.
    """
    bc_topology = BroadCastTopology(src, dsts, num_partitions)

    # Track how many partitions (unique) use each edge (u, v)
    used_counts = defaultdict(int)

    # Constants controlling trade-off between cost and congestion/throughput
    # These are intentionally mild to keep cost as the primary factor.
    STATIC_THROUGHPUT_PENALTY = 0.003  # $/GB scaled by 1/throughput
    USE_PENALTY_COEF = 0.02           # $/GB per (partition use / throughput)

    # Pre-prepare to speed-up attribute access
    # Ensure the graph has required attributes; set defaults if missing
    for u, v, data in G.edges(data=True):
        if "cost" not in data or data["cost"] is None:
            data["cost"] = 0.0
        if "throughput" not in data or data["throughput"] is None:
            data["throughput"] = 1.0

    def weight_func(u, v, data):
        # Get base cost and throughput with safe defaults
        cost = data.get("cost", 0.0)
        thr = data.get("throughput", 1.0)
        if thr is None or thr <= 0:
            thr = 0.01  # avoid division by zero; strongly penalize near-zero throughput

        uc = used_counts[(u, v)]
        # Mild static penalty to prefer higher-throughput edges all else equal,
        # and congestion penalty that grows with number of partitions already using the edge.
        w = cost + (STATIC_THROUGHPUT_PENALTY / thr) + (USE_PENALTY_COEF * uc / thr)
        return w

    # For each partition, compute a shortest-path tree from src to all destinations using dynamic weights
    for p in range(num_partitions):
        # Compute single-source Dijkstra with custom weight function
        try:
            lengths, paths = nx.single_source_dijkstra(G, source=src, weight=weight_func)
        except Exception:
            # As a robust fallback, use cost-only weight
            lengths, paths = nx.single_source_dijkstra(G, source=src, weight=lambda u, v, d: d.get("cost", 0.0))

        # Collect edges used by this partition across all destination paths (de-duplicated per edge)
        edges_used_this_partition = set()

        for dst in dsts:
            # If destination unreachable under dynamic weights, fallback to unweighted shortest path
            path_nodes = paths.get(dst, None)
            if path_nodes is None:
                try:
                    path_nodes = nx.shortest_path(G, src, dst)  # BFS fallback
                except Exception:
                    # As last resort, try a dijkstra on cost
                    try:
                        path_nodes = nx.dijkstra_path(G, src, dst, weight=lambda u, v, d: d.get("cost", 0.0))
                    except Exception:
                        # If still unreachable, skip (though test cases should ensure reachability)
                        continue

            # Convert nodes path to edges and append to topology
            for i in range(len(path_nodes) - 1):
                u = path_nodes[i]
                v = path_nodes[i + 1]
                edge_data = G[u][v]
                bc_topology.append_dst_partition_path(dst, p, [u, v, edge_data])
                edges_used_this_partition.add((u, v))

        # Update used_counts once per edge for this partition
        for e in edges_used_this_partition:
            used_counts[e] += 1

    return bc_topology
"""
        return {"code": code}