import networkx as nx
import random
import math

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import networkx as nx
import random
import math
from collections import defaultdict

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
    # Constants based on problem description
    N_VM = 2  # Default setup
    HOURLY_RATE = 0.54
    SEC_RATE = HOURLY_RATE / 3600.0
    
    # Limits per region type (Gbps)
    LIMITS = {
        'aws': {'ingress': 10.0, 'egress': 5.0},
        'gcp': {'ingress': 16.0, 'egress': 7.0},
        'azure': {'ingress': 16.0, 'egress': 16.0}
    }

    def get_limits(node):
        provider = node.split(':')[0]
        lim = LIMITS.get(provider, {'ingress': 10.0, 'egress': 5.0})
        # Limits are multiplied by number of VMs per region
        return lim['ingress'] * N_VM, lim['egress'] * N_VM

    # 1. Generate Candidate Trees (SPTs)
    # We generate a few different spanning trees to choose from.
    # - Tree 0: Optimal Cost (Weight = cost)
    # - Tree 1: Optimal Hops (Weight = 1) - proxy for minimizing latency/bottlenecks
    # - Tree 2-5: Randomized Cost (Weight = cost * random) to find near-optimal alternatives
    
    candidate_trees = []
    
    def extract_tree(path_dict):
        tree = {}
        valid = True
        for dst in dsts:
            if dst in path_dict:
                node_list = path_dict[dst]
                edge_list = []
                for i in range(len(node_list)-1):
                    u, v = node_list[i], node_list[i+1]
                    if G.has_edge(u, v):
                        edge_list.append((u, v, G[u][v]))
                    else:
                        valid = False; break
                tree[dst] = edge_list
            else:
                tree[dst] = []
        return tree if valid else None

    # Tree 0: Pure Cost
    try:
        paths = nx.shortest_path(G, source=src, weight='cost')
        t = extract_tree(paths)
        if t: candidate_trees.append(t)
    except: pass

    # Tree 1: Min Hops
    try:
        paths = nx.shortest_path(G, source=src)
        t = extract_tree(paths)
        if t: candidate_trees.append(t)
    except: pass

    # Trees 2-5: Randomized Cost
    for _ in range(4):
        def noisy_weight(u, v, d):
            # Perturb cost by +/- 15% to find diverse cost-effective paths
            return d.get('cost', 0.1) * random.uniform(0.85, 1.15)
        try:
            paths = nx.shortest_path(G, source=src, weight=noisy_weight)
            t = extract_tree(paths)
            if t: candidate_trees.append(t)
        except: pass
        
    if not candidate_trees:
        return BroadCastTopology(src, dsts, num_partitions)

    # Pre-process tree structure for fast evaluation
    # Store just the set of edges and nodes used by each tree
    tree_data = []
    for tree in candidate_trees:
        active_edges = set()
        active_nodes = set()
        active_nodes.add(src)
        for dst, path in tree.items():
            for (u, v, d) in path:
                active_edges.add((u, v))
                active_nodes.add(u)
                active_nodes.add(v)
        tree_data.append({'edges': list(active_edges), 'nodes': active_nodes})

    # 2. Greedy Optimization
    # State: assignment[partition_id] = tree_index
    # Goal: Minimize Total Cost (Egress + Instance)
    
    assignment = [0] * num_partitions # Start with Cost Optimal for all
    
    def evaluate(curr_assignment):
        # Count partitions per edge
        edge_partition_counts = defaultdict(int)
        total_active_nodes = set()
        total_active_nodes.add(src)
        
        for p_id, t_idx in enumerate(curr_assignment):
            td = tree_data[t_idx]
            total_active_nodes.update(td['nodes'])
            for edge in td['edges']:
                edge_partition_counts[edge] += 1
                
        c_egress = 0.0
        max_transfer_time = 0.0
        
        # Determine degrees for bandwidth allocation logic
        node_out_deg = defaultdict(int)
        node_in_deg = defaultdict(int)
        for (u, v), count in edge_partition_counts.items():
            if count > 0:
                node_out_deg[u] += 1
                node_in_deg[v] += 1
                
        # Compute costs
        for (u, v), count in edge_partition_counts.items():
            if count == 0: continue
            
            data = G[u][v]
            # Egress Cost: sum(|Pe| * s * c). Using s=1 as linear proxy for optimization.
            c_egress += count * data.get('cost', 0.0)
            
            # Transfer Time Calculation
            cap = data.get('throughput', 1000.0)
            u_out_lim = get_limits(u)[1]
            v_in_lim = get_limits(v)[0]
            
            # Bandwidth allocation rule: limit / num_edges
            alloc_src = u_out_lim / node_out_deg[u] if node_out_deg[u] > 0 else float('inf')
            alloc_dst = v_in_lim / node_in_deg[v] if node_in_deg[v] > 0 else float('inf')
            
            f_e = min(cap, alloc_src, alloc_dst)
            if f_e < 1e-9: f_e = 1e-9
            
            # Time = Volume / Rate. Proxy Volume = count * 8 bits
            t = (count * 8.0) / f_e
            if t > max_transfer_time:
                max_transfer_time = t
                
        # Instance Cost = |V| * n_vm * rate * time
        c_instance = len(total_active_nodes) * N_VM * SEC_RATE * max_transfer_time
        return c_egress + c_instance

    current_cost = evaluate(assignment)
    
    # Hill Climbing: Try to move each partition to a better tree
    # 2 passes is sufficient to settle on a good configuration
    for _ in range(2):
        indices = list(range(num_partitions))
        random.shuffle(indices)
        changed = False
        for p_id in indices:
            best_t = assignment[p_id]
            best_local_cost = current_cost
            original_t = assignment[p_id]
            
            for t_idx in range(len(candidate_trees)):
                if t_idx == original_t: continue
                
                assignment[p_id] = t_idx
                new_cost = evaluate(assignment)
                
                if new_cost < best_local_cost:
                    best_local_cost = new_cost
                    best_t = t_idx
                else:
                    assignment[p_id] = original_t
            
            if best_t != original_t:
                assignment[p_id] = best_t
                current_cost = best_local_cost
                changed = True
        
        if not changed:
            break

    # 3. Build Topology
    topology = BroadCastTopology(src, dsts, num_partitions)
    for p_id, t_idx in enumerate(assignment):
        tree = candidate_trees[t_idx]
        for dst in dsts:
            path_list = []
            for (u, v, d) in tree[dst]:
                path_list.append([u, v, d])
            topology.set_dst_partition_paths(dst, p_id, path_list)
            
    return topology
"""
        return {"code": code}
