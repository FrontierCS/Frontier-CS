import os
import inspect
import statistics
from typing import List, Dict, Any
import networkx as nx


class BroadCastTopology:
    def __init__(self, src: str, dsts: List[str], num_partitions: int):
        self.src = src
        self.dsts = dsts
        self.num_partitions = int(num_partitions)
        # Structure: {dst: {partition_id: [edges]}}
        # Each edge is [src_node, dst_node, edge_data_dict]
        self.paths: Dict[str, Dict[str, List[List[Any]]]] = {
            dst: {str(i): None for i in range(self.num_partitions)} for dst in dsts
        }

    def append_dst_partition_path(self, dst: str, partition: int, path: List[Any]):
        """
        Append an edge to the path for a specific destination-partition pair.

        Args:
            dst: Destination node
            partition: Partition ID (0 to num_partitions-1)
            path: Edge represented as [src_node, dst_node, edge_data_dict]
                  where edge_data_dict = G[src_node][dst_node]
        """
        partition_str = str(partition)
        if self.paths[dst][partition_str] is None:
            self.paths[dst][partition_str] = []
        self.paths[dst][partition_str].append(path)

    def set_dst_partition_paths(self, dst: str, partition: int, paths: List[List[Any]]):
        """
        Set the complete path (list of edges) for a destination-partition pair.

        Args:
            dst: Destination node
            partition: Partition ID
            paths: List of edges, each edge is [src_node, dst_node, edge_data_dict]
        """
        partition_str = str(partition)
        self.paths[dst][partition_str] = paths

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

    if num_partitions <= 0:
        return bc_topology

    # Precompute a combined edge weight that trades off cost and throughput
    costs = []
    inv_thrs = []
    eps_thr = 1e-9

    for _, _, data in G.edges(data=True):
        c = float(data.get("cost", 0.0))
        thr = float(data.get("throughput", 1.0))
        if thr <= 0.0:
            thr = eps_thr
        costs.append(c)
        inv_thrs.append(1.0 / thr)

    if costs and inv_thrs:
        med_cost = statistics.median(costs)
        med_invthr = statistics.median(inv_thrs)
        if med_cost > 0.0 and med_invthr > 0.0:
            lambda_time = 0.25 * med_cost / med_invthr
        else:
            lambda_time = 0.0
    else:
        lambda_time = 0.0

    for u, v, data in G.edges(data=True):
        c = float(data.get("cost", 0.0))
        thr = float(data.get("throughput", 1.0))
        if thr <= 0.0:
            thr = eps_thr
        inv_thr = 1.0 / thr
        data["weight"] = c + lambda_time * inv_thr

    max_paths_per_dst = 3

    for dst in dsts:
        if src == dst:
            # Trivial case: source is destination; zero-hop paths
            for part_id in range(num_partitions):
                bc_topology.set_dst_partition_paths(dst, part_id, [])
            continue

        # Generate up to K candidate paths using the combined weight
        path_candidates: List[List[str]] = []
        try:
            k = min(max_paths_per_dst, num_partitions)
            gen = nx.shortest_simple_paths(G, src, dst, weight="weight")
            for path in gen:
                path_candidates.append(path)
                if len(path_candidates) >= k:
                    break
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            path_candidates = []

        if not path_candidates:
            # Fallback to pure cost-based shortest path
            try:
                path = nx.dijkstra_path(G, src, dst, weight="cost")
                path_candidates = [path]
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                # If still no path (shouldn't happen in valid configs), skip this dst
                continue

        # Compute metrics for each candidate path
        path_metrics = []  # (path, total_cost, min_throughput, alloc_weight)
        for path in path_candidates:
            total_cost = 0.0
            min_thr = float("inf")
            for u, v in zip(path[:-1], path[1:]):
                edata = G[u][v]
                total_cost += float(edata.get("cost", 0.0))
                thr = float(edata.get("throughput", 1.0))
                if thr <= 0.0:
                    thr = eps_thr
                if thr < min_thr:
                    min_thr = thr
            if min_thr == float("inf"):
                min_thr = eps_thr
            alloc_weight = min_thr / (total_cost + 1e-9)
            path_metrics.append((path, total_cost, min_thr, alloc_weight))

        # Sort paths by decreasing alloc_weight (prefer fast & cheap)
        path_metrics.sort(key=lambda x: x[3], reverse=True)

        K = len(path_metrics)
        counts = [0] * K

        if num_partitions >= K:
            for i in range(K):
                counts[i] = 1
            remaining = num_partitions - K
        else:
            # num_partitions < K: assign one partition to the best num_partitions paths
            for i in range(num_partitions):
                counts[i] = 1
            remaining = 0

        if remaining > 0:
            sum_weights = sum(m[3] for m in path_metrics)
            if sum_weights <= 0.0:
                # If all weights are zero, distribute round-robin
                idx = 0
                while remaining > 0:
                    counts[idx % K] += 1
                    idx += 1
                    remaining -= 1
            else:
                float_alloc = []
                for idx, (_, _, _, w) in enumerate(path_metrics):
                    frac = (w / sum_weights) * remaining
                    base_int = int(frac)
                    float_alloc.append((idx, base_int, frac - base_int))

                # First assign base_int portions without exceeding remaining
                for idx, base_int, _ in float_alloc:
                    if remaining <= 0:
                        break
                    if base_int > 0:
                        add = min(base_int, remaining)
                        counts[idx] += add
                        remaining -= add

                # Distribute any leftover based on fractional parts
                if remaining > 0:
                    float_alloc.sort(key=lambda t: t[2], reverse=True)
                    i = 0
                    while remaining > 0 and i < len(float_alloc):
                        idx = float_alloc[i][0]
                        counts[idx] += 1
                        remaining -= 1
                        i += 1

                # Any residual (should not happen) is spread round-robin
                idx = 0
                while remaining > 0:
                    counts[idx % K] += 1
                    remaining -= 1
                    idx += 1

        # Final adjustment to ensure total counts equals num_partitions
        total_assigned = sum(counts)
        if total_assigned != num_partitions:
            diff = num_partitions - total_assigned
            counts[-1] += diff

        # Map partitions to paths
        partition_paths: List[List[str]] = [None] * num_partitions  # type: ignore
        p_idx = 0
        for path_idx, (path, _, _, _) in enumerate(path_metrics):
            for _ in range(counts[path_idx]):
                if p_idx >= num_partitions:
                    break
                partition_paths[p_idx] = path
                p_idx += 1

        # Fallback in case of any None entries (should not occur)
        default_path = path_metrics[0][0]
        for i in range(num_partitions):
            if partition_paths[i] is None:
                partition_paths[i] = default_path

        # Construct BroadCastTopology entries
        for part_id in range(num_partitions):
            path = partition_paths[part_id]
            edges_list: List[List[Any]] = []
            for u, v in zip(path[:-1], path[1:]):
                edge_data = G[u][v]
                edges_list.append([u, v, edge_data])
            bc_topology.set_dst_partition_paths(dst, part_id, edges_list)

    return bc_topology


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/algorithm.py"}
        """
        program_path = inspect.getfile(inspect.currentframe())
        return {"program_path": program_path}
