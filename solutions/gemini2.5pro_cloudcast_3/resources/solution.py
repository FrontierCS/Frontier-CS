import sys

# Per problem spec, the solution must be a class named Solution.
# The `solve` method should return the algorithm as a string or path.
# Returning as a string is the most self-contained and robust approach.
class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Generates and returns the Python code for the broadcast optimization algorithm.
        """
        
        # The algorithm code is encapsulated in a single string.
        # This string includes all necessary imports, class definitions, and the
        # main search_algorithm function. This makes the submission self-contained.
        algorithm_code = '''
import networkx as nx
import itertools

class BroadCastTopology:
    """
    A class to store and manage the broadcast topology paths.
    This class is provided by the evaluation environment but is included here
    for completeness and to make the algorithm code self-contained.
    """
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
    # --- Constants and Heuristics ---
    N_VM = 2
    R_INSTANCE = 0.54  # $/hour

    # Determine K, the number of diverse paths for load balancing.
    # The logic ensures K=1 for a single partition, and then ramps up
    # to a max of 8 paths to spread the load for multiple partitions.
    if num_partitions <= 1:
        K = 1
    else:
        K = min(8, max(2, num_partitions // 2))

    # --- Composite Edge Weight Calculation ---
    # The total cost is a sum of egress and instance costs. Instance cost is
    # proportional to transfer time, which is inversely related to throughput.
    # We define a composite edge weight to balance these two factors:
    # effective_cost = egress_cost + (time_cost_factor / throughput)
    
    # Estimate the number of nodes involved to approximate the time_cost_factor.
    num_nodes_approx = len(G.nodes())
    
    # This factor, X, models the instance cost component per GB transferred over an edge.
    # X = |V| * n_vm * (r_instance / 3600) * 8 bits/byte
    X = num_nodes_approx * N_VM * (R_INSTANCE / 3600) * 8

    # Pre-calculate and assign the composite weight to each edge in the graph.
    for u, v, data in G.edges(data=True):
        cost = data.get('cost', 0.0)
        throughput = data.get('throughput', 1e-9)
        # Prevent division by zero or negative throughput.
        if throughput <= 1e-9:
            throughput = 1e-9
        data['effective_cost'] = cost + X / throughput

    # --- Topology Construction ---
    bc_topology = BroadCastTopology(src, dsts, num_partitions)

    for dst in dsts:
        # 1. Find K shortest simple paths using the composite weight.
        candidate_node_paths = []
        try:
            paths_generator = nx.shortest_simple_paths(G, src, dst, weight='effective_cost')
            candidate_node_paths = list(itertools.islice(paths_generator, K))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass

        # Fallback 1: If no path is found, try again using only egress cost.
        if not candidate_node_paths:
            try:
                paths_generator = nx.shortest_simple_paths(G, src, dst, weight='cost')
                candidate_node_paths = list(itertools.islice(paths_generator, K))
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                pass
        
        # Fallback 2: As a last resort, find an unweighted shortest path.
        if not candidate_node_paths:
            try:
                path = nx.shortest_path(G, src, dst)
                candidate_node_paths = [path]
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                # If the destination is unreachable, we must skip it.
                continue

        num_found_paths = len(candidate_node_paths)

        # 2. Distribute partitions across the found paths in a round-robin fashion.
        # This simple load balancing strategy helps avoid congestion and reduces max transfer time.
        for p_id in range(num_partitions):
            path_idx = p_id % num_found_paths
            node_path = candidate_node_paths[path_idx]
            
            # Convert the node path to the required edge path format.
            edge_path = []
            for i in range(len(node_path) - 1):
                u, v = node_path[i], node_path[i + 1]
                edge_data = G[u][v]
                edge_path.append([u, v, edge_data])
            
            bc_topology.set_dst_partition_paths(dst, p_id, edge_path)
            
    return bc_topology
'''
        return {"code": algorithm_code}
