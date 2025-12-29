import networkx as nx

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        algorithm_code = r"""
import networkx as nx
import heapq
import collections

class BroadCastTopology:
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
    # Heuristic Constants
    DATA_VOL_ESTIMATE = 300.0  # GB
    INSTANCE_COST_HR = 0.54
    NUM_VMS = 2
    LIMITS = {
        'aws': {'ingress': 10.0, 'egress': 5.0},
        'gcp': {'ingress': 16.0, 'egress': 7.0},
        'azure': {'ingress': 16.0, 'egress': 16.0}
    }

    def get_provider(node_name):
        return node_name.split(':')[0]

    # Steiner Tree Heuristic: Successive Shortest Path from growing tree
    # Builds a multicast tree connecting src to all dsts
    def build_tree(weight_type='cost', penalty_edges=None):
        tree_nodes = {src}
        tree_edges = set()
        remaining_dsts = set(dsts) - {src}
        
        # To reconstruct
        parents = {n: None for n in G.nodes}
        
        while remaining_dsts:
            pq = []
            min_dist = {n: float('inf') for n in G.nodes}
            parents = {n: None for n in G.nodes}
            
            # Initialize PQ with all nodes currently in the tree
            for u in tree_nodes:
                min_dist[u] = 0
                heapq.heappush(pq, (0, u))
            
            found_dst = None
            visited = set()
            
            while pq:
                d, u = heapq.heappop(pq)
                if u in visited: continue
                visited.add(u)
                
                if u in remaining_dsts:
                    found_dst = u
                    break
                
                if d > min_dist[u]: continue
                
                for v in G.neighbors(u):
                    if v in visited or v in tree_nodes: continue
                    
                    edata = G[u][v]
                    w = 1.0
                    if weight_type == 'cost':
                        w = edata.get('cost', 0.0) + 1e-5
                    
                    # Apply penalty to encourage diversity
                    if penalty_edges and (u, v) in penalty_edges:
                        w *= 5.0
                        
                    if min_dist[u] + w < min_dist[v]:
                        min_dist[v] = min_dist[u] + w
                        parents[v] = u
                        heapq.heappush(pq, (min_dist[v], v))
            
            if found_dst:
                # Backtrack adding to tree
                curr = found_dst
                while curr not in tree_nodes:
                    p = parents[curr]
                    if p is None: break
                    tree_edges.add((p, curr))
                    tree_nodes.add(curr)
                    curr = p
                remaining_dsts.remove(found_dst)
            else:
                break
                
        # Convert tree edges to paths for each destination
        paths = {}
        adj = collections.defaultdict(list)
        for u, v in tree_edges:
            adj[u].append(v)
            
        q = [(src, [])]
        while q:
            u, p = q.pop(0)
            if u in dsts:
                paths[u] = p
            for v in adj[u]:
                q.append((v, p + [[u, v, G[u][v]]]))
                
        # Handle fallback for any unreachable destinations
        for d in dsts:
            if d not in paths:
                try:
                    sp = nx.shortest_path(G, src, d, weight='cost')
                    p = []
                    for i in range(len(sp)-1):
                        p.append([sp[i], sp[i+1], G[sp[i]][sp[i+1]]])
                    paths[d] = p
                except:
                    paths[d] = []
        return paths, tree_edges

    # Generate Candidate Topologies
    candidates = []
    
    # 1. Min Cost Tree
    p1, e1 = build_tree('cost')
    candidates.append(p1)
    
    # 2. Diverse Min Cost Tree (penalize first tree's edges)
    p2, e2 = build_tree('cost', penalty_edges=e1)
    candidates.append(p2)
    
    # 3. Min Hops Tree (often correlates with throughput/latency)
    p3, e3 = build_tree('hops')
    candidates.append(p3)
    
    # Evaluate Partition Assignment Strategies
    strategies = []
    # Strategy A: All partitions on Min Cost Tree
    strategies.append([0] * num_partitions)
    # Strategy B: Load balance between Tree 1 and Tree 2
    strategies.append([i % 2 for i in range(num_partitions)])
    # Strategy C: Load balance between Tree 1 and Tree 3
    strategies.append([0 if i % 2 == 0 else 2 for i in range(num_partitions)])
    
    best_strat = strategies[0]
    min_score = float('inf')
    
    part_size = DATA_VOL_ESTIMATE / max(1, num_partitions)
    
    for strat in strategies:
        edge_parts = collections.defaultdict(set)
        inv_nodes = set()
        
        # Calculate usage
        for pid, tid in enumerate(strat):
            paths = candidates[tid]
            for d in dsts:
                if d in paths:
                    for u, v, _ in paths[d]:
                        edge_parts[(u,v)].add(pid)
                        inv_nodes.add(u)
                        inv_nodes.add(v)
        
        # Estimate Egress Cost
        egress_cost = 0.0
        node_out = collections.defaultdict(int)
        node_in = collections.defaultdict(int)
        
        for (u, v), pset in edge_parts.items():
            egress_cost += len(pset) * part_size * G[u][v].get('cost', 0)
            node_out[u] += 1
            node_in[v] += 1
            
        # Estimate Instance Cost (via Transfer Time)
        max_time = 0.0
        for (u, v), pset in edge_parts.items():
            flow_gb = len(pset) * part_size
            flow_bits = flow_gb * 8
            
            p_u = get_provider(u)
            p_v = get_provider(v)
            
            lim_out = LIMITS.get(p_u, LIMITS['aws'])['egress'] * NUM_VMS
            lim_in = LIMITS.get(p_v, LIMITS['aws'])['ingress'] * NUM_VMS
            
            # Bottleneck on this link
            cap = min(G[u][v].get('throughput', 1.0),
                      lim_out / max(1, node_out[u]),
                      lim_in / max(1, node_in[v]))
                      
            t = flow_bits / max(0.001, cap)
            if t > max_time: max_time = t
            
        inst_cost = len(inv_nodes) * NUM_VMS * (INSTANCE_COST_HR / 3600.0) * max_time
        total = egress_cost + inst_cost
        
        if total < min_score:
            min_score = total
            best_strat = strat
            
    # Construct Result
    res = BroadCastTopology(src, dsts, num_partitions)
    for pid, tid in enumerate(best_strat):
        paths = candidates[tid]
        for d in dsts:
            if d in paths:
                res.set_dst_partition_paths(d, pid, paths[d])
                
    return res
"""
        return {"code": algorithm_code}