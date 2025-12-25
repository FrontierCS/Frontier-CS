class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dictionary containing the Python code for the search algorithm
        as a string.
        """
        
        python_code_string = """
import networkx as nx
from itertools import islice

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
    Designs broadcast topology by finding multiple, load-balanced paths for data partitions.

    This algorithm balances two competing objectives:
    1. Minimize egress cost: This favors paths with low 'cost' attributes.
    2. Minimize instance cost: This is influenced by transfer time, which is
       dominated by network bottlenecks. To minimize this, we need to use
       high-throughput paths and distribute traffic to avoid congestion.

    Strategy:
    - Use a composite edge weight for pathfinding that combines egress cost
      and a penalty for low throughput. The weight is defined as:
      weight = cost + beta / throughput.
    - For each destination, find K-shortest paths using this composite weight.
    - Distribute the data partitions across these K paths in a round-robin
      fashion to balance the load, thus preventing bottlenecks and reducing
      overall transfer time.
    """
    bc_topology = BroadCastTopology(src, dsts, num_partitions)

    # This beta parameter balances the trade-off between cost and throughput.
    # A higher beta prioritizes faster (high throughput) paths, while a lower
    # beta prioritizes cheaper (low cost) paths. The value is chosen heuristically
    # to make the cost and throughput terms comparable in magnitude for typical network values.
    beta = 0.1

    # Pre-calculate and add the composite weight to each edge in the graph.
    for u, v, data in G.edges(data=True):
        cost = data.get('cost', 0.0)
        # Use a small epsilon for throughput to avoid division by zero.
        throughput = data.get('throughput', 1e-9)
        if throughput <= 0:
            throughput = 1e-9
        G.edges[u, v]['composite_weight'] = cost + beta / throughput

    # Determine the number of alternative paths (K) to use for load balancing.
    # Capped at a small number (5) to keep the k-shortest-paths search efficient,
    # as its complexity increases with K.
    k = min(num_partitions, 5)
    
    # If there are no partitions, return an empty topology.
    if k == 0:
        return bc_topology

    for dst in dsts:
        node_paths = []
        try:
            # Find K shortest simple paths from source to destination using the composite weight.
            paths_generator = nx.shortest_simple_paths(G, src, dst, weight='composite_weight')
            node_paths = list(islice(paths_generator, k))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            # This can happen if src or dst is not in the graph, or no path exists.
            # We'll proceed to the fallback logic.
            pass

        if not node_paths:
            # Fallback strategy: If composite weight search fails (e.g., due to infinite
            # weights from zero throughput), try again using only the 'cost'. This ensures
            # that we find a path if one exists, prioritizing cost.
            try:
                path = nx.dijkstra_path(G, src, dst, weight='cost')
                node_paths = [path]
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                # If there's still no path, we cannot route to this destination.
                # The evaluator will see missing paths for this destination.
                continue
        
        # Distribute partitions over the found paths in a round-robin fashion.
        # This simple load balancing helps to avoid creating a single, highly
        # congested path.
        for i in range(num_partitions):
            # Assign partition i to one of the K paths.
            path_nodes = node_paths[i % len(node_paths)]
            
            # Convert the list of nodes into a list of edges for the topology object.
            edge_path = []
            for j in range(len(path_nodes) - 1):
                u, v = path_nodes[j], path_nodes[j+1]
                edge_path.append([u, v, G[u][v]])
            
            bc_topology.set_dst_partition_paths(dst, i, edge_path)
            
    return bc_topology
"""
        return {"code": python_code_string}
