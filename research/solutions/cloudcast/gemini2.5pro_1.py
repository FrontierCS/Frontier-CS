class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dictionary containing the Python code for the search algorithm.
        The code is provided as a self-contained string.
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
    Designs routing paths for broadcasting data partitions to multiple destinations
    using an iterative, load-balancing approach.

    The algorithm iteratively assigns a path for each (partition, destination) pair.
    It uses Dijkstra's algorithm with a dynamic edge weight function. This weight
    is a composite of three factors:
    1. Egress cost ($/GB): The direct monetary cost of data transfer.
    2. Latency penalty: Proportional to the inverse of the edge's throughput,
       favoring faster links.
    3. Congestion penalty: Increases as an edge is used by more partitions,
       encouraging load balancing and path diversity to reduce bottlenecks.

    This strategy aims to find a holistic solution that minimizes the complex,
    non-linear total cost function by balancing egress costs, instance costs (by
    controlling path diversity), and transfer time (by avoiding congestion).
    """
    bc_topology = BroadCastTopology(src, dsts, num_partitions)

    # Hyperparameters for the dynamic edge weight function. These are chosen
    # based on analysis of the cost function to balance different objectives.
    
    # C: Trades off egress cost ($/GB) vs. latency (proportional to 1/Gbps).
    # A value derived from typical problem parameters to make the two terms
    # of the cost function comparable.
    C = 0.075

    # alpha: Controls the penalty for edge congestion. A higher value promotes
    # finding diverse, disjoint paths, which is good for reducing transfer time
    # but may increase the number of active nodes (instance cost).
    alpha = 1.5

    # Keep track of how many partitions use each edge.
    edge_usage = defaultdict(int)

    def dynamic_weight_func(u, v, d):
        """
        Calculates a dynamic weight for an edge for use in Dijkstra's algorithm.
        """
        # Base cost combines egress cost and a latency-related penalty.
        # A small epsilon is added to throughput to prevent division by zero.
        base_cost = d.get('cost', 0.0) + C / (d.get('throughput', 1.0) + 1e-9)
        
        # Congestion penalty grows linearly with the number of partitions using the edge.
        congestion_penalty = 1.0 + alpha * edge_usage.get((u, v), 0)
        
        return base_cost * congestion_penalty

    # Iteratively find a path for each partition going to each destination.
    # The order of iteration (partitions first, then destinations) promotes
    # a balanced distribution of load across the entire broadcast task from the start.
    for partition_id in range(num_partitions):
        # Sort destinations to ensure deterministic behavior, which is good for
        # reproducibility and debugging.
        for dst in sorted(dsts):
            try:
                # Find the shortest path using the dynamic weight function which
                # accounts for the current load on the network.
                path_nodes = nx.dijkstra_path(G, src, dst, weight=dynamic_weight_func)
            except nx.NetworkXNoPath:
                # This case should not happen in the given problem, but as a
                # safeguard, we skip any unreachable destinations.
                continue

            # Convert the list of nodes into a list of edges with their attributes.
            path_edges = []
            for i in range(len(path_nodes) - 1):
                u, v = path_nodes[i], path_nodes[i+1]
                path_edges.append([u, v, G[u][v]])
                
                # Update the usage count for each edge in the chosen path.
                # This will increase its weight for subsequent path searches.
                edge_usage[(u, v)] += 1
            
            # Store the computed path in the topology object.
            bc_topology.set_dst_partition_paths(dst, partition_id, path_edges)

    return bc_topology
"""
        return {"code": algorithm_code}