import sys
import os

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with the Python code for the search algorithm.
        """
        # Note: The file path is not used in this implementation as the
        # algorithm is self-contained and does not need to read from
        # the spec file. The evaluation environment passes parameters
        # directly to the search_algorithm function.
        
        algorithm_code = """
import networkx as nx
from collections import defaultdict
import itertools

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
    \"\"\"
    Designs broadcast paths using a K-shortest paths algorithm combined with
    greedy load balancing to minimize total cost.

    The strategy is as follows:
    1.  For each destination, find K low-cost candidate paths. The number of
        paths K is chosen based on the number of partitions to allow for
        effective load distribution.
    2.  Iterate through each partition for each destination.
    3.  In each step, greedily assign the partition to the candidate path
        that is currently the least congested. Congestion is measured by the
        maximum number of partitions already assigned to any single edge
        along the path.
    4.  Ties in congestion are broken by choosing the path with the lower
        total egress cost.
    5.  This approach aims to balance the load across the network to minimize
        the maximum transfer time (which depends on edge congestion), while
        still preferring low-cost paths to keep egress costs down.
    \"\"\"

    unique_dsts = set(dsts)
    bc_topology = BroadCastTopology(src, dsts, num_partitions)

    if num_partitions == 0:
        return bc_topology
        
    K = max(1, min(num_partitions, 10))
    candidate_paths = {}

    for dst in unique_dsts:
        if dst == src:
            candidate_paths[dst] = [[]]
            continue
        
        try:
            paths_generator = nx.shortest_simple_paths(G, source=src, target=dst, weight='cost')
            
            dst_paths = []
            for i, node_path in enumerate(paths_generator):
                if i >= K:
                    break
                edge_path = []
                for j in range(len(node_path) - 1):
                    u, v = node_path[j], node_path[j+1]
                    edge_path.append((u, v))
                dst_paths.append(edge_path)
            candidate_paths[dst] = dst_paths
        except nx.NetworkXNoPath:
            candidate_paths[dst] = []

        if not candidate_paths.get(dst):
            try:
                if nx.has_path(G, src, dst):
                    node_path = nx.shortest_path(G, src, dst)
                    edge_path = []
                    for j in range(len(node_path) - 1):
                        u, v = node_path[j], node_path[j+1]
                        edge_path.append((u, v))
                    candidate_paths[dst] = [edge_path]
            except nx.NetworkXNoPath:
                 candidate_paths[dst] = []

    path_costs = defaultdict(list)
    for dst, paths in candidate_paths.items():
        for path in paths:
            cost = sum(G[u][v]['cost'] for u, v in path)
            path_costs[dst].append(cost)

    edge_loads = defaultdict(int)

    for p_id in range(num_partitions):
        # Using a stable sort for destinations to ensure deterministic behavior
        sorted_dsts = sorted(list(unique_dsts))
        for dst in sorted_dsts:
            
            if not candidate_paths.get(dst):
                continue

            best_path_idx = -1
            min_max_load = float('inf')
            min_path_cost = float('inf')

            for i, path in enumerate(candidate_paths[dst]):
                current_max_load = 0
                if path:
                    for u, v in path:
                        current_max_load = max(current_max_load, edge_loads.get((u, v), 0))
                
                path_cost = path_costs[dst][i]

                if current_max_load < min_max_load:
                    min_max_load = current_max_load
                    min_path_cost = path_cost
                    best_path_idx = i
                elif current_max_load == min_max_load and path_cost < min_path_cost:
                    min_path_cost = path_cost
                    best_path_idx = i
            
            if best_path_idx != -1:
                chosen_path_edges = candidate_paths[dst][best_path_idx]
                path_with_data = [[u, v, G[u][v]] for u, v in chosen_path_edges]
                
                bc_topology.set_dst_partition_paths(dst, p_id, path_with_data)

                for u, v in chosen_path_edges:
                    edge_loads[(u, v)] += 1
    
    # Handle original dsts list which may have duplicates.
    # The calculated paths for a unique destination `d` will be used for all occurrences of `d` in `dsts`.
    # We need to fill the topology object for all keys in the original dsts list.
    for dst in dsts:
        if dst in bc_topology.paths:
            for p_id in range(num_partitions):
                partition_str = str(p_id)
                # The path is already computed and stored under the unique dst key.
                # We just need to make sure the final object has the same structure.
                # The constructor already handles creating keys for all items in dsts.
                bc_topology.paths[dst][partition_str] = bc_topology.paths[dst][partition_str]

    return bc_topology
"""
        return {"code": algorithm_code}