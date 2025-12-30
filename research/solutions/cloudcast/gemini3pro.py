import networkx as nx

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        algorithm_code = """
import networkx as nx

class BroadCastTopology:
    def __init__(self, src: str, dsts: list[str], num_partitions: int):
        self.src = src
        self.dsts = dsts
        self.num_partitions = int(num_partitions)
        # Structure: {dst: {partition_id: [edges]}}
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
    
    # Helper to build a tree based on current weights
    def build_tree(graph, source, destinations, weight_attr):
        tree_paths = {}
        try:
            # Dijkstra for Shortest Path Tree
            length, path_dict = nx.single_source_dijkstra(graph, source, weight=weight_attr)
            for dst in destinations:
                if dst in path_dict:
                    p = path_dict[dst]
                    tree_paths[dst] = []
                    # Convert node list to edge list with data from original G
                    for i in range(len(p) - 1):
                        u, v = p[i], p[i+1]
                        # Use G for original data to satisfy API requirement
                        tree_paths[dst].append([u, v, G[u][v]])
                else:
                    tree_paths[dst] = []
        except Exception:
            # Handle unreachability or errors gracefully
            for dst in destinations:
                if dst not in tree_paths:
                    tree_paths[dst] = []
        return tree_paths

    # Function to calculate actual egress cost of a tree (sum of costs of unique edges)
    # This acts as the quality metric for the tree
    def calculate_tree_metric(tree_paths):
        unique_edges = set()
        for dst, edges in tree_paths.items():
            for u, v, data in edges:
                unique_edges.add((u, v))
        
        cost = 0.0
        for u, v in unique_edges:
            cost += G[u][v].get("cost", 0.0)
        return cost

    # Working graph copy for weight manipulation
    W = G.copy()
    
    # Initialize weights: Cost + small throughput penalty (inverse throughput)
    # This favors high bandwidth links when costs are similar, helping with instance cost (transfer time)
    for u, v, data in W.edges(data=True):
        c = data.get("cost", 0.0)
        t = data.get("throughput", 1.0)
        if t <= 1e-6: t = 1e-6
        # Weight formula: cost + (0.001 / throughput)
        # 0.001 acts as a tie-breaker factor
        data["weight"] = c + (1e-3 / t)
    
    candidate_trees = []
    
    # --- Tree 0: Primary Shortest Path Tree (Minimizes Cost) ---
    tree0 = build_tree(W, src, dsts, "weight")
    metric0 = calculate_tree_metric(tree0)
    candidate_trees.append((tree0, metric0))
    
    # --- Tree 1: Alternative with penalties (Maximizes Diversity) ---
    # Identify edges used in Tree 0
    edges_in_0 = set()
    for dst, paths in tree0.items():
        for u, v, d in paths:
            edges_in_0.add((u, v))
            
    # Apply penalty to used edges in W to encourage finding different paths
    # Penalty factor 2.0 discourages reuse but allows it if no other viable path exists
    for u, v in edges_in_0:
        if W.has_edge(u, v):
            W[u][v]["weight"] *= 2.0 
            
    tree1 = build_tree(W, src, dsts, "weight")
    metric1 = calculate_tree_metric(tree1)
    
    # Acceptance threshold: Alternative tree must not be >10% more expensive in egress cost
    # If it's too expensive, the throughput gain won't offset the egress cost increase
    if metric1 <= 1.1 * metric0:
        candidate_trees.append((tree1, metric1))
        
        # --- Tree 2: Second Alternative ---
        edges_in_1 = set()
        for dst, paths in tree1.items():
            for u, v, d in paths:
                edges_in_1.add((u, v))
        
        # Penalize edges used in Tree 1 as well
        for u, v in edges_in_1:
            if W.has_edge(u, v):
                W[u][v]["weight"] *= 2.0
                
        tree2 = build_tree(W, src, dsts, "weight")
        metric2 = calculate_tree_metric(tree2)
        
        if metric2 <= 1.1 * metric0:
             candidate_trees.append((tree2, metric2))
    
    # Construct Topology
    topo = BroadCastTopology(src, dsts, num_partitions)
    
    num_candidates = len(candidate_trees)
    
    # Assign partitions Round-Robin to the selected valid trees
    # This distributes load across the network if multiple efficient trees exist
    for i in range(num_partitions):
        tree_idx = i % num_candidates
        selected_tree = candidate_trees[tree_idx][0]
        
        for dst in dsts:
            path = selected_tree.get(dst, [])
            topo.set_dst_partition_paths(dst, i, path)
            
    return topo
"""
        return {"code": algorithm_code}