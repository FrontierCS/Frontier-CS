import json


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        algo_code = '''
import networkx as nx
from itertools import islice
from typing import List, Dict, Tuple


class BroadCastTopology:
    def __init__(self, src: str, dsts: List[str], num_partitions: int):
        self.src = src
        self.dsts = dsts
        self.num_partitions = int(num_partitions)
        # Structure: {dst: {partition_id: [edges]}}
        # Each edge is [src_node, dst_node, edge_data_dict]
        self.paths = {
            dst: {str(i): None for i in range(self.num_partitions)}
            for dst in dsts
        }

    def append_dst_partition_path(self, dst: str, partition: int, path: list):
        """
        Append an edge to the path for a specific destination-partition pair.

        Args:
            dst: Destination node
            partition: Partition ID (0 to num_partitions-1)
            path: Edge represented as [src_node, dst_node, edge_data_dict]
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
        self.num_partitions = int(num_partitions)


def search_algorithm(src: str, dsts: List[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    """
    Design routing paths for broadcasting data partitions to multiple destinations.
    """
    # Small constant to avoid division by zero
    EPS_THROUGHPUT = 1e-9
    # Max number of candidate paths per destination
    MAX_K = 10
    # Static tradeoff between egress cost and throughput in initial path search
    GAMMA = 0.06
    # Dynamic penalty weight for already-used edges when assigning partitions
    ALPHA = 0.25

    if num_partitions is None:
        num_partitions = 1
    num_partitions = int(num_partitions)
    if num_partitions <= 0:
        num_partitions = 1

    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    if not dsts:
        return bc_topology

    # Global load counter per directed edge (u, v)
    edge_load: Dict[Tuple[str, str], int] = {}

    for dst in dsts:
        # Handle degenerate case where dst == src
        if dst == src:
            for pid in range(num_partitions):
                bc_topology.set_dst_partition_paths(dst, pid, [])
            continue

        K = min(MAX_K, num_partitions)

        # Combined weight: egress cost + GAMMA * (1 / throughput)
        def weight(u, v, data):
            cost = data.get("cost", 0.0)
            throughput = data.get("throughput", 0.0) or EPS_THROUGHPUT
            return float(cost) + GAMMA * (1.0 / float(throughput))

        candidate_paths_nodes: List[List[str]] = []

        # Try K-shortest simple paths using combined weight
        try:
            path_generator = nx.shortest_simple_paths(G, source=src, target=dst, weight=weight)
            for path_nodes in islice(path_generator, K):
                if len(path_nodes) >= 2:
                    candidate_paths_nodes.append(path_nodes)
        except Exception:
            candidate_paths_nodes = []

        # Fallback: shortest path by pure cost
        if not candidate_paths_nodes:
            try:
                path_nodes = nx.dijkstra_path(G, src, dst, weight="cost")
                if len(path_nodes) >= 2:
                    candidate_paths_nodes = [path_nodes]
            except Exception:
                # Last-resort fallback: unweighted shortest path
                try:
                    path_nodes = nx.shortest_path(G, src, dst)
                    if len(path_nodes) >= 2:
                        candidate_paths_nodes = [path_nodes]
                except Exception:
                    # No path exists; set empty paths (should not occur in valid configs)
                    for pid in range(num_partitions):
                        bc_topology.set_dst_partition_paths(dst, pid, [])
                    continue

        # Convert candidate node-paths into edge-paths and cache edge data
        candidate_edges: List[List[Tuple[str, str, dict]]] = []
        for nodes in candidate_paths_nodes:
            edges_for_path: List[Tuple[str, str, dict]] = []
            for u, v in zip(nodes[:-1], nodes[1:]):
                if u == v:
                    continue  # ignore potential self-loops
                edge_data = G[u][v]
                edges_for_path.append((u, v, edge_data))
            if edges_for_path:
                candidate_edges.append(edges_for_path)

        if not candidate_edges:
            # Should not happen if graph is valid
            for pid in range(num_partitions):
                bc_topology.set_dst_partition_paths(dst, pid, [])
            continue

        # Assign each partition to the best candidate path considering current edge loads
        for pid in range(num_partitions):
            best_idx = 0
            best_score = float("inf")

            for idx, edges in enumerate(candidate_edges):
                score = 0.0
                for (u, v, data) in edges:
                    cost_e = data.get("cost", 0.0)
                    throughput = data.get("throughput", 0.0) or EPS_THROUGHPUT
                    load = edge_load.get((u, v), 0)
                    # Cost plus dynamic congestion penalty
                    score += float(cost_e) + ALPHA * (load + 1) / float(throughput)
                # Tiny penalty on hop count to mildly discourage long paths
                score += 1e-4 * len(edges)

                if score < best_score:
                    best_score = score
                    best_idx = idx

            chosen_edges = candidate_edges[best_idx]

            # Update global edge loads
            for (u, v, _data) in chosen_edges:
                edge_load[(u, v)] = edge_load.get((u, v), 0) + 1

            # Store chosen path for this (dst, partition)
            edge_list = [[u, v, data] for (u, v, data) in chosen_edges]
            bc_topology.set_dst_partition_paths(dst, pid, edge_list)

    return bc_topology
'''
        return {"code": algo_code}