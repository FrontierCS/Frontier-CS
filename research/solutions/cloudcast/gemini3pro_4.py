import networkx as nx
import inspect
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

    for dst in dsts:
        # Strategy: Use K-Shortest Paths to find alternative routes with similar cost.
        # This allows load balancing partitions across different paths to minimize 
        # bandwidth bottlenecks while keeping egress cost low.
        
        candidates = []
        try:
            # Retrieve up to 3 shortest paths based on cost.
            # Using islice on the generator is efficient for large graphs.
            candidates = list(islice(nx.shortest_simple_paths(G, src, dst, weight="cost"), 3))
        except nx.NetworkXNoPath:
            continue
            
        if not candidates:
            continue

        # Calculate total cost for each candidate path
        candidate_costs = []
        for path in candidates:
            cost = 0.0
            for i in range(len(path) - 1):
                u, v = path[i], path[i+1]
                cost += G[u][v].get("cost", 0.0)
            candidate_costs.append(cost)
        
        min_cost = candidate_costs[0]
        
        # Filter paths: only keep those within 15% of the minimum cost.
        # This prevents selecting significantly more expensive paths just for load balancing.
        valid_paths = []
        for i, path in enumerate(candidates):
            if candidate_costs[i] <= min_cost * 1.15:
                # Format path as list of [u, v, data] edges
                formatted_path = []
                for j in range(len(path) - 1):
                    u, v = path[j], path[j+1]
                    formatted_path.append([u, v, G[u][v]])
                valid_paths.append(formatted_path)
        
        # Fallback safety: ensure at least one path is used
        if not valid_paths:
            path = candidates[0]
            formatted_path = []
            for j in range(len(path) - 1):
                u, v = path[j], path[j+1]
                formatted_path.append([u, v, G[u][v]])
            valid_paths.append(formatted_path)

        # Distribute partitions round-robin across the valid paths
        num_valid = len(valid_paths)
        for i in range(num_partitions):
            selected_path = valid_paths[i % num_valid]
            bc_topology.set_dst_partition_paths(dst, i, selected_path)

    return bc_topology

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with the solution code.
        """
        header = "import networkx as nx\nfrom itertools import islice\n\n"
        topo_src = inspect.getsource(BroadCastTopology)
        algo_src = inspect.getsource(search_algorithm)
        
        return {
            "code": header + topo_src + "\n" + algo_src
        }