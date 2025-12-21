import os
import json
import math
import heapq
from typing import List, Dict, Tuple, Set
import networkx as nx


class BroadCastTopology:
    def __init__(self, src: str, dsts: List[str], num_partitions: int):
        self.src = src
        self.dsts = dsts
        self.num_partitions = int(num_partitions)
        # Structure: {dst: {partition_id: [edges]}}
        # Each edge is [src_node, dst_node, edge_data_dict]
        self.paths = {dst: {str(i): None for i in range(self.num_partitions)} for dst in dsts}

    def append_dst_partition_path(self, dst: str, partition: int, path: list):
        """
        Append an edge to the path for a specific destination-partition pair.

        Args:
            dst: Destination node
            partition: Partition ID (0 to num_partitions-1)
            path: Edge represented as [src_node, dst_node, edge_data_dict]
                  where edge_data_dict = G[src_node][dst_node]
        """
        partition = str(partition)
        if self.paths[dst][partition] is None:
            self.paths[dst][partition] = []
        self.paths[dst][partition].append(path)

    def set_dst_partition_paths(self, dst: str, partition: int, paths: list):
        """
        Set the complete path (list of edges) for a destination-partition pair.

        Args:
            dst: Destination node
            partition: Partition ID
            paths: List of edges, each edge is [src_node, dst_node, edge_data_dict]
        """
        partition = str(partition)
        self.paths[dst][partition] = paths

    def set_num_partitions(self, num_partitions: int):
        """Update number of partitions"""
        self.num_partitions = num_partitions


def search_algorithm(src: str, dsts: List[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    """
    Design routing paths for broadcasting data partitions to multiple destinations.

    Args:
        src: Source node (e.g., "aws:ap-northeast-1")
        dsts: List of destination nodes (e.g., ["aws:us-east-1", "gcp:us-central1"])
        G: NetworkX DiGraph with edge attributes:
           - "cost": float ($/GB) - egress cost for transferring data
           - "throughput": float (Gbps) - maximum bandwidth capacity
        num_partitions: Number of data partitions to broadcast

    Returns:
        BroadCastTopology object with routing paths for all (destination, partition) pairs
    """
    bc_topology = BroadCastTopology(src, dsts, num_partitions)

    # Deduplicate destinations while preserving order
    seen_dsts: Set[str] = set()
    unique_dsts: List[str] = []
    for d in dsts:
        if d not in seen_dsts:
            seen_dsts.add(d)
            unique_dsts.append(d)

    # Edge load: number of partitions that use this edge (for P_e)
    load: Dict[Tuple[str, str], int] = {}

    # Parameters controlling trade-off between egress cost and load/throughput
    alpha = 0.1   # penalty per existing partition using an edge (multiplicative on cost)
    gamma = 0.005  # small additive penalty scaled by 1/throughput

    INF = float("inf")

    # Precompute adjacency to speed up Dijkstra
    # G[u] is already adjacency dict: {v: data}
    for partition_id in range(num_partitions):
        # Dijkstra from src with weights depending on current load
        dist: Dict[str, float] = {src: 0.0}
        parent: Dict[str, str] = {}
        heap: List[Tuple[float, str]] = [(0.0, src)]

        while heap:
            d, u = heapq.heappop(heap)
            if d != dist.get(u, INF):
                continue
            # Explore outgoing edges
            for v, data in G[u].items():
                if v == u:
                    continue  # avoid self-loops
                base_cost = float(data.get("cost", 0.0))
                th = float(data.get("throughput", 1.0))
                if th <= 0.0:
                    th = 1e-9
                l = load.get((u, v), 0)
                w = base_cost * (1.0 + alpha * l) + gamma / th
                nd = d + w
                if nd < dist.get(v, INF):
                    dist[v] = nd
                    parent[v] = u
                    heapq.heappush(heap, (nd, v))

        used_edges_in_partition: Set[Tuple[str, str]] = set()

        # For each destination, reconstruct path and update topology and load
        for dst in unique_dsts:
            # Handle src == dst: no transfer needed
            if dst == src:
                continue

            path_nodes: List[str] = []

            if dst in dist:
                # Reconstruct using parent pointers
                cur = dst
                while True:
                    path_nodes.append(cur)
                    if cur == src:
                        break
                    cur = parent.get(cur)
                    if cur is None:
                        # This should not happen for reachable nodes; break and fallback
                        path_nodes = []
                        break
                if path_nodes:
                    path_nodes.reverse()
            # Fallback: use pure cost-based shortest path if needed
            if not path_nodes or path_nodes[0] != src:
                try:
                    path_nodes = nx.shortest_path(
                        G,
                        src,
                        dst,
                        weight=lambda u, v, d: float(d.get("cost", 0.0)),
                    )
                except Exception:
                    # If still no path, skip (graph likely invalid, but avoid crash)
                    continue

            if len(path_nodes) < 2:
                continue

            # Append edges to BroadCastTopology and update load once per edge per partition
            for i in range(len(path_nodes) - 1):
                u = path_nodes[i]
                v = path_nodes[i + 1]
                edge_data = G[u][v]
                bc_topology.append_dst_partition_path(dst, partition_id, [u, v, edge_data])
                ekey = (u, v)
                if ekey not in used_edges_in_partition:
                    used_edges_in_partition.add(ekey)
                    load[ekey] = load.get(ekey, 0) + 1

    return bc_topology


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/algorithm.py"}
        """
        # Use this file itself as the program containing search_algorithm
        return {"program_path": os.path.abspath(__file__)}
