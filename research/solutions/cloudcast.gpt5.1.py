import json


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        algorithm_code = '''import networkx as nx
from collections import defaultdict


class BroadCastTopology:
    def __init__(self, src: str, dsts: list[str], num_partitions: int):
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

    def set_dst_partition_paths(self, dst: str, partition: int, paths: list[list]):
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


def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    """
    Design routing paths for broadcasting data partitions to multiple destinations.

    Heuristic:
    - Generate up to K candidate low-cost paths per destination.
    - Assign partitions one-by-one across all destinations.
    - For each assignment, pick the path minimizing:
          normalized_cost + lambda_t * normalized_time_proxy
      where time_proxy ~ max_e ( (current_load_e + 1) / throughput_e )
      and both terms are normalized using graph-wide averages.
    """
    bc_topology = BroadCastTopology(src, dsts, num_partitions)

    if num_partitions <= 0:
        return bc_topology

    # -----------------------------
    # Global graph statistics for normalization
    # -----------------------------
    total_cost = 0.0
    total_inv_thr = 0.0
    edge_count = 0

    for u, v, data in G.edges(data=True):
        c = data.get("cost", 0.0)
        thr = data.get("throughput", 1.0)
        if thr <= 0:
            thr = 1e-3
        total_cost += c
        total_inv_thr += 1.0 / thr
        edge_count += 1

    if edge_count == 0:
        # Degenerate graph; nothing meaningful to do
        return bc_topology

    avg_cost = total_cost / edge_count
    avg_inv_thr = total_inv_thr / edge_count

    if avg_cost <= 0:
        avg_cost = 1.0
    if avg_inv_thr <= 0:
        avg_inv_thr = 1.0

    # Relative weight between normalized cost and normalized time proxy
    lambda_t = 1.0

    # -----------------------------
    # Candidate paths per destination
    # -----------------------------
    K_MAX = 8  # max number of candidate paths per destination

    candidate_paths_nodes: dict[str, list[list[str]]] = {}
    path_edges: dict[str, list[list[tuple[str, str]]]] = {}
    path_cost_norm: dict[str, list[float]] = {}

    for dst in dsts:
        paths_for_dst: list[list[str]] = []
        try:
            gen = nx.shortest_simple_paths(G, src, dst, weight="cost")
            for _ in range(K_MAX):
                try:
                    p = next(gen)
                except StopIteration:
                    break
                if len(p) >= 2:
                    paths_for_dst.append(p)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            paths_for_dst = []

        # Fallback to unweighted shortest path if we did not find any candidate
        if not paths_for_dst:
            try:
                p = nx.shortest_path(G, src, dst)
                if len(p) >= 2:
                    paths_for_dst = [p]
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                paths_for_dst = []

        candidate_paths_nodes[dst] = paths_for_dst
        path_edges[dst] = []
        path_cost_norm[dst] = []

        for p in paths_for_dst:
            edges = []
            cost_sum = 0.0
            valid = True
            for i in range(len(p) - 1):
                u = p[i]
                v = p[i + 1]
                if not G.has_edge(u, v):
                    valid = False
                    break
                data = G[u][v]
                c = data.get("cost", 0.0)
                cost_sum += c
                edges.append((u, v))
            if not valid or not edges:
                continue
            path_edges[dst].append(edges)
            path_cost_norm[dst].append(cost_sum / avg_cost)

        # If still empty (very unlikely), there is no viable path; leave as is.

    # -----------------------------
    # Greedy assignment of partitions to paths
    # -----------------------------
    edge_load: defaultdict[tuple[str, str], int] = defaultdict(int)

    # Round-robin over partitions, then destinations, to spread load more evenly
    for part in range(num_partitions):
        for dst in dsts:
            paths = path_edges.get(dst)
            if not paths:
                # Last-resort fallback: compute a single cheapest path on the fly
                try:
                    p = nx.dijkstra_path(G, src, dst, weight="cost")
                    edges = []
                    cost_sum = 0.0
                    for i in range(len(p) - 1):
                        u = p[i]
                        v = p[i + 1]
                        if not G.has_edge(u, v):
                            edges = []
                            break
                        data = G[u][v]
                        c = data.get("cost", 0.0)
                        cost_sum += c
                        edges.append((u, v))
                    if edges:
                        paths = [edges]
                        path_edges[dst] = paths
                        path_cost_norm[dst] = [cost_sum / avg_cost]
                    else:
                        continue
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    continue

            best_idx = 0
            best_score = None

            for idx, edges in enumerate(paths):
                # Compute normalized time proxy if we assign this partition to this path
                max_time_ratio = 0.0
                for (u, v) in edges:
                    data = G[u][v]
                    thr = data.get("throughput", 1.0)
                    if thr <= 0:
                        thr = 1e-3
                    load = edge_load[(u, v)] + 1  # hypothetical new load
                    inv_thr = 1.0 / thr
                    time_ratio = (load * inv_thr) / avg_inv_thr
                    if time_ratio > max_time_ratio:
                        max_time_ratio = time_ratio

                score = path_cost_norm[dst][idx] + lambda_t * max_time_ratio

                if best_score is None or score < best_score:
                    best_score = score
                    best_idx = idx

            chosen_edges = paths[best_idx]

            # Update edge loads
            for (u, v) in chosen_edges:
                edge_load[(u, v)] += 1

            # Materialize path as list of [src_node, dst_node, edge_data_dict]
            edge_paths = []
            for (u, v) in chosen_edges:
                edge_paths.append([u, v, G[u][v]])

            bc_topology.set_dst_partition_paths(dst, part, edge_paths)

    return bc_topology
'''
        return {"code": algorithm_code}