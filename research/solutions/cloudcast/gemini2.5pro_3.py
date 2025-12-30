import networkx as nx

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with the Python code for the search algorithm.
        """
        
        algorithm_code = """
import networkx as nx
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
        \"\"\"
        Append an edge to the path for a specific destination-partition pair.

        Args:
            dst: Destination node
            partition: Partition ID (0 to num_partitions-1)
            path: Edge represented as [src_node, dst_node, edge_data_dict]
                  where edge_data_dict = G[src_node][dst_node]
        \"\"\"
        partition = str(partition)
        if self.paths[dst][partition] is None:
            self.paths[dst][partition] = []
        self.paths[dst][partition].append(path)

    def set_dst_partition_paths(self, dst: str, partition: int, paths: list[list]):
        \"\"\"
        Set the complete path (list of edges) for a destination-partition pair.

        Args:
            dst: Destination node
            partition: Partition ID
            paths: List of edges, each edge is [src_node, dst_node, edge_data_dict]
        \"\"\"
        partition = str(partition)
        self.paths[dst][partition] = paths

    def set_num_partitions(self, num_partitions: int):
        \"\"\"Update number of partitions\"\"\"
        self.num_partitions = num_partitions


def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> 'BroadCastTopology':
    \"\"\"
    Designs optimal routing paths for broadcasting data partitions.

    The strategy is a two-phase approach:
    1. Path Finding: For each destination, find K diverse, low-cost paths using an 
       iterative Dijkstra's algorithm with edge weight penalties. This provides a
       set of good candidate routes. The edge weight is primarily cost, with a
       small tie-breaker for higher throughput to choose better paths when costs are equal.
    2. Partition Assignment: Greedily assign each partition (for each destination)
       to the candidate path that is currently the least congested. Congestion is
       measured by the maximum number of partitions already assigned to any edge
       along the path. This balances the load across the network, minimizing the
       maximum traffic on any single link, which is key to reducing transfer time
       and overall instance costs.
    \"\"\"
    bc_topology = BroadCastTopology(src, dsts, num_partitions)

    if num_partitions == 0:
        return bc_topology

    # Heuristic for the number of diverse paths (K) to find per destination.
    K = min(num_partitions, 8) if num_partitions > 1 else 1

    edge_partition_counts = defaultdict(int)
    all_candidate_paths = {}

    # Phase 1: Find K diverse candidate paths for each destination
    for dst in dsts:
        temp_G = G.copy()
        
        for u, v, data in temp_G.edges(data=True):
            cost = float(data.get('cost', 1e9))
            throughput = float(data.get('throughput', 1e-9))
            # Use cost as primary weight, with throughput as a minor tie-breaker
            data['temp_weight'] = cost - 1e-12 * throughput

        candidate_paths_for_dst = []
        for _ in range(K):
            try:
                path_nodes = nx.dijkstra_path(temp_G, src, dst, weight='temp_weight')
                
                if len(path_nodes) > 1:
                    candidate_paths_for_dst.append(path_nodes)
                    # Penalize edges on the found path to encourage diversity
                    penalty_factor = 1.5
                    for u, v in zip(path_nodes[:-1], path_nodes[1:]):
                        if temp_G.has_edge(u, v):
                            temp_G[u][v]['temp_weight'] *= penalty_factor
                else:
                    break
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                break

        # Fallback to a single shortest path if the iterative method fails
        if not candidate_paths_for_dst:
            try:
                path_nodes = nx.dijkstra_path(G, src, dst, weight='cost')
                if path_nodes:
                    candidate_paths_for_dst.append(path_nodes)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                # Destination is unreachable, skip it
                continue
        
        all_candidate_paths[dst] = candidate_paths_for_dst

    # Phase 2: Greedily assign partitions to the least congested paths
    for p_id in range(num_partitions):
        for dst in dsts:
            candidate_paths = all_candidate_paths.get(dst)
            if not candidate_paths:
                continue

            best_path_nodes = None
            min_max_congestion = float('inf')

            # Find the least congested path among the pre-computed candidates
            for path_nodes in candidate_paths:
                max_congestion_on_path = 0
                for u, v in zip(path_nodes[:-1], path_nodes[1:]):
                    max_congestion_on_path = max(max_congestion_on_path, edge_partition_counts[(u, v)])
                
                if max_congestion_on_path < min_max_congestion:
                    min_max_congestion = max_congestion_on_path
                    best_path_nodes = path_nodes
            
            # Default to the first path (lowest cost) if all have same congestion
            if best_path_nodes is None:
                best_path_nodes = candidate_paths[0]

            # Assign partition, update congestion counts, and set path in topology
            edge_path_for_topology = []
            for u, v in zip(best_path_nodes[:-1], best_path_nodes[1:]):
                edge_partition_counts[(u, v)] += 1
                edge_data = G.get_edge_data(u, v)
                if edge_data:
                    edge_path_for_topology.append([u, v, edge_data])
            
            bc_topology.set_dst_partition_paths(dst, p_id, edge_path_for_topology)

    return bc_topology
"""
        return {"code": algorithm_code}