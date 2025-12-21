import networkx as nx

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": """import networkx as nx

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
    topology = BroadCastTopology(src, dsts, num_partitions)
    
    # Pre-calculate base weights with epsilon for tie-breaking
    base_weights = {}
    for u, v, data in G.edges(data=True):
        cost = data.get('cost', 0.0)
        base_weights[(u, v)] = cost + 1e-7

    # Track edge usage to balance load across partitions
    edge_usage = {e: 0 for e in G.edges()}
    
    unique_dsts = set(dsts)
    if src in unique_dsts:
        unique_dsts.remove(src)
        for p in range(num_partitions):
            topology.set_dst_partition_paths(src, p, [])
            
    for p in range(num_partitions):
        # Steiner Tree Approximation with Capacity Penalty
        # We build a tree connecting src to all dsts minimizing a weighted cost.
        # Weights logic:
        # - 0 if edge is already in current tree (multicast benefit: pay once per partition)
        # - (cost + epsilon) * (1 + penalty * usage) if new edge (load balancing)
        
        current_tree_edges = set()
        reached_nodes = {src}
        unreached = set(unique_dsts)
        
        while unreached:
            # Create a graph copy to apply dynamic weights
            temp_G = G.copy()
            for u, v in temp_G.edges():
                if (u, v) in current_tree_edges:
                    w = 0.0
                else:
                    usage = edge_usage.get((u, v), 0)
                    base = base_weights.get((u, v), 1e-7)
                    # Penalty factor: 0.5 implies 50% cost increase per overlapping partition
                    # This encourages distributing partitions across different paths
                    w = base * (1.0 + 0.5 * usage)
                temp_G[u][v]['dyn_weight'] = w
            
            # Find closest unreached node to the current tree set
            try:
                dists, paths = nx.multi_source_dijkstra(temp_G, reached_nodes, weight='dyn_weight')
            except Exception:
                break
                
            best_node = None
            min_dist = float('inf')
            
            # Filter results for unreached destinations
            candidates = [n for n in unreached if n in dists]
            
            if not candidates:
                break
                
            for n in candidates:
                if dists[n] < min_dist:
                    min_dist = dists[n]
                    best_node = n
            
            if best_node:
                # Add the found path to the tree
                path = paths[best_node]
                for i in range(len(path) - 1):
                    u, v = path[i], path[i+1]
                    current_tree_edges.add((u, v))
                    reached_nodes.add(v)
                
                # Update unreached set
                unreached = {n for n in unreached if n not in reached_nodes}
            else:
                break
        
        # Update global usage counts for future partitions
        for u, v in current_tree_edges:
            edge_usage[(u, v)] += 1
            
        # Reconstruct paths from the tree for this partition
        # Build adjacency list for the tree
        tree_adj = {u: [] for u in G.nodes()}
        for u, v in current_tree_edges:
            tree_adj[u].append(v)
            
        # BFS to build parent map for path reconstruction
        parent_map = {}
        queue = [src]
        visited_tree = {src}
        
        while queue:
            curr = queue.pop(0)
            for neighbor in tree_adj[curr]:
                if neighbor not in visited_tree:
                    visited_tree.add(neighbor)
                    parent_map[neighbor] = curr
                    queue.append(neighbor)
        
        # Set paths for all destinations
        for dst in unique_dsts:
            if dst in visited_tree:
                path_edges = []
                curr = dst
                while curr != src:
                    par = parent_map[curr]
                    path_edges.append([par, curr, G[par][curr]])
                    curr = par
                path_edges.reverse()
                topology.set_dst_partition_paths(dst, p, path_edges)
            else:
                # Fallback: Shortest path on original graph if Steiner heuristic failed to connect
                try:
                    path_nodes = nx.shortest_path(G, src, dst, weight='cost')
                    edges = []
                    for i in range(len(path_nodes)-1):
                        u, v = path_nodes[i], path_nodes[i+1]
                        edges.append([u, v, G[u][v]])
                    topology.set_dst_partition_paths(dst, p, edges)
                except nx.NetworkXNoPath:
                    pass

    return topology
"""
        }
