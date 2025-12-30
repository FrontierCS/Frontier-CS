import networkx as nx

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code_str = r'''
import networkx as nx
import heapq

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
    Uses an iterative shortest-path approach with penalty updates to achieve load balancing
    and minimize total cost (egress + instance time).
    """
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    
    # Track usage of edges across partitions to penalize congestion
    # Key: (u, v), Value: number of partitions utilizing this link
    edge_usage = {}
    
    # Parameters for the heuristic weight function
    # PENALTY_FACTOR: Increases effective cost of an edge based on usage count
    # to encourage spreading partitions across different paths (Load Balancing).
    PENALTY_FACTOR = 0.5 
    
    # THROUGHPUT_BIAS: Small inverse term to prefer higher throughput links when costs are similar
    THROUGHPUT_BIAS = 1e-5

    # Iterate through each partition to find an optimal multicast tree
    for partition_id in range(num_partitions):
        
        # Build a temporary graph with dynamic weights for this partition
        G_temp = nx.DiGraph()
        
        for u, v, data in G.edges(data=True):
            # Extract basic edge attributes
            cost = data.get('cost', 0.1)
            throughput = data.get('throughput', 1.0)
            
            # Avoid division by zero
            if throughput <= 0:
                throughput = 0.001
            
            # Get current usage count
            usage = edge_usage.get((u, v), 0)
            
            # Calculate dynamic weight
            # Objective: Minimize Egress Cost + Minimize Time (maximize throughput/minimize congestion)
            # Weight = BaseCost * (1 + penalty * usage) + Small/Throughput
            
            # The penalty term ensures that if an edge is used by previous partitions,
            # subsequent partitions perceive it as more expensive, encouraging path diversity.
            weight = cost * (1.0 + PENALTY_FACTOR * usage) + (THROUGHPUT_BIAS / throughput)
            
            G_temp.add_edge(u, v, weight=weight)
            
        # Compute Shortest Path Tree (SPT) from source to all nodes using Dijkstra
        # This approximates a Steiner Tree for the current partition
        try:
            # single_source_dijkstra returns (distance_dict, path_dict)
            _, paths = nx.single_source_dijkstra(G_temp, source=src, weight='weight')
        except nx.NetworkXNoPath:
            # If source is isolated (edge case)
            continue
            
        # Assign paths for each destination
        for dst in dsts:
            if dst in paths:
                node_path = paths[dst]
                path_edges = []
                
                # Convert list of nodes to list of edges with data
                for i in range(len(node_path) - 1):
                    u, v = node_path[i], node_path[i+1]
                    
                    # Use original graph data for the topology result
                    edge_data = G[u][v]
                    path_edges.append([u, v, edge_data])
                    
                    # Update usage count for the edge
                    # This affects the weights for the next partition loop
                    edge_usage[(u, v)] = edge_usage.get((u, v), 0) + 1
                
                bc_topology.set_dst_partition_paths(dst, partition_id, path_edges)
            else:
                # Destination unreachable
                pass

    return bc_topology
'''
        return {"code": code_str}