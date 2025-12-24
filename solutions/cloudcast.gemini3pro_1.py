import networkx as nx
import sys

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
    
    Strategy:
    1. Construct multiple diverse routing trees (approximate Steiner Trees) from source to all destinations.
    2. Diversity is achieved by iterative penalization of edge weights (cost).
    3. Distribute partitions across these trees to balance load and reduce congestion (transfer time),
       while keeping the total egress cost low by using small penalty factors.
    """
    topo = BroadCastTopology(src, dsts, num_partitions)
    
    # Configuration
    # Penalty factor 1.2: Prefer reusing edges if alternative is >20% more expensive.
    # This balances Egress Cost (primary) vs Time (secondary).
    PENALTY_FACTOR = 1.2 
    MAX_TREES = 4 # Cap on number of trees to generate
    
    num_trees = min(num_partitions, MAX_TREES)
    if num_trees < 1: 
        num_trees = 1

    # Create a working graph with calculated weights
    # Weight = Cost + small_epsilon / Throughput
    # This prioritizes Cost, but breaks ties using Throughput.
    G_work = G.copy()
    for u, v, data in G_work.edges(data=True):
        c = data.get('cost', 0.0)
        t = data.get('throughput', 1.0)
        # 1e-6 is small enough to not interfere with cost optimization
        # unless costs are identical.
        data['weight'] = c + (1e-6 / t)

    candidate_trees = [] # List of {dst: list_of_edges}

    for _ in range(num_trees):
        # Compute Shortest Path Tree from src using current weights
        try:
            # dijkstra_predecessor_and_distance returns (preds, dists)
            # preds is dict {node: [predecessors]}
            preds, _ = nx.dijkstra_predecessor_and_distance(G_work, src, weight='weight')
        except nx.NetworkXNoPath:
            break
            
        tree_paths = {}
        used_edges = set()
        
        # Reconstruct paths
        valid_tree = True
        for dst in dsts:
            if dst not in preds:
                valid_tree = False
                break
            
            path_edges = []
            curr = dst
            while curr != src:
                # Get predecessor
                ps = preds.get(curr)
                if not ps:
                    valid_tree = False
                    break
                prev = ps[0] # Pick first predecessor
                
                # Retrieve original edge data
                if G.has_edge(prev, curr):
                    edge_data = G[prev][curr]
                    path_edges.append([prev, curr, edge_data])
                    used_edges.add((prev, curr))
                else:
                    valid_tree = False
                    break
                curr = prev
            
            if not valid_tree:
                break
            
            path_edges.reverse() # Order: Src -> Dst
            tree_paths[dst] = path_edges
        
        if not valid_tree:
            break
            
        candidate_trees.append(tree_paths)
        
        # Update weights in G_work to penalize used edges
        for u, v in used_edges:
            if G_work.has_edge(u, v):
                w = G_work[u][v]['weight']
                new_w = w * PENALTY_FACTOR
                # Add small base penalty to ensure 0-cost edges also get diversified if needed
                if new_w == w:
                    new_w += 1e-5
                G_work[u][v]['weight'] = new_w

    # If something failed and no trees found (unlikely), return empty topo
    if not candidate_trees:
        return topo

    # Assign partitions to the generated trees in Round-Robin fashion
    count = len(candidate_trees)
    for p_id in range(num_partitions):
        tree_idx = p_id % count
        selected_tree = candidate_trees[tree_idx]
        
        for dst in dsts:
            if dst in selected_tree:
                topo.set_dst_partition_paths(dst, p_id, selected_tree[dst])

    return topo

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": open(__file__).read()}
