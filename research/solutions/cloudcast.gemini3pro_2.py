import networkx as nx

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": """
import networkx as nx
import heapq

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
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    
    # Helper function to build a Steiner Tree approximation
    # Uses an iterative Dijkstra approach (Prim-like for Steiner Tree)
    # Modifies weights of used edges to 0 to encourage multicast tree formation
    def get_steiner_tree(base_graph, weight_key):
        sim_G = base_graph.copy()
        
        # Map: node -> parent in tree
        parent_map = {src: None}
        reached = {src}
        unreached = set(dsts)
        
        while unreached:
            # Find the closest unreached destination from the current tree (reached set)
            try:
                dists, paths = nx.multi_source_dijkstra(sim_G, reached, weight=weight_key)
            except Exception:
                # Disconnected graph or error
                break
                
            closest_node = None
            min_dist = float('inf')
            
            for t in unreached:
                if t in dists and dists[t] < min_dist:
                    min_dist = dists[t]
                    closest_node = t
            
            if closest_node is None:
                break
                
            # Add the path to the tree
            path_nodes = paths[closest_node]
            # path_nodes is [start_node (in reached), ... , closest_node]
            
            for i in range(len(path_nodes) - 1):
                u = path_nodes[i]
                v = path_nodes[i+1]
                
                if v not in parent_map:
                    parent_map[v] = u
                    reached.add(v)
                    # Set weight to 0 in sim_G so subsequent paths can reuse this edge for free
                    if sim_G.has_edge(u, v):
                        sim_G[u][v][weight_key] = 0
            
            unreached.discard(closest_node)
            
        # Reconstruct paths for API format
        dst_paths = {}
        for dst in dsts:
            if dst not in parent_map:
                # Fallback to simple shortest path if Steiner heuristic failed for some node
                try:
                    p = nx.shortest_path(G, src, dst, weight='cost')
                    edges = []
                    for i in range(len(p)-1):
                        edges.append([p[i], p[i+1], G[p[i]][p[i+1]]])
                    dst_paths[dst] = edges
                except:
                    dst_paths[dst] = []
                continue
            
            # Backtrack from dst to src
            path_edges = []
            curr = dst
            while curr != src:
                par = parent_map.get(curr)
                if par is None: 
                    break
                # Use original graph data
                path_edges.append([par, curr, G[par][curr]])
                curr = par
            
            dst_paths[dst] = list(reversed(path_edges))
            
        return dst_paths

    # Strategy:
    # 1. Build Tree 0 optimizing purely for Cost (min Egress Cost)
    # 2. Build Tree 1 optimizing for Cost but penalizing edges used in Tree 0 (Load Balancing)
    # 3. Distribute partitions between these trees
    
    # Tree 0: Min Cost
    tree0 = get_steiner_tree(G, 'cost')
    
    # Tree 1: Diversity
    G_div = G.copy()
    
    # Identify edges used in Tree 0
    used_in_t0 = set()
    for d in dsts:
        for edge in tree0[d]:
            u, v = edge[0], edge[1]
            used_in_t0.add((u, v))
            
    # Apply penalty to used edges
    for u, v, data in G_div.edges(data=True):
        cost = data.get('cost', 0.1) # default nonzero to avoid issues
        if (u, v) in used_in_t0:
            # Multiply cost by 1.5 to prefer other paths if they aren't too expensive
            data['cost'] = cost * 1.5
    
    tree1 = get_steiner_tree(G_div, 'cost')
    
    trees = [tree0, tree1]
    
    # Assign partitions
    for p in range(num_partitions):
        # Round robin assignment
        t_idx = p % 2
        selected_tree = trees[t_idx]
        
        for dst in dsts:
            bc_topology.set_dst_partition_paths(dst, p, selected_tree[dst])

    return bc_topology
"""}