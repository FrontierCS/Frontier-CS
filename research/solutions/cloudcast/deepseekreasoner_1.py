import json
import networkx as nx
import itertools
import heapq
import math
from collections import defaultdict, deque

def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int):
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    
    # Extract provider from node name (e.g., "aws:us-east-1" -> "aws")
    def get_provider(node):
        return node.split(':')[0]
    
    # For each partition, try to find good paths to all destinations
    # using a tree-based approach with load balancing
    for partition in range(num_partitions):
        # Build a flow network for this partition
        # Use Dijkstra from source with cost as weight
        distances = {}
        prev = {}
        pq = [(0, src, None)]
        
        while pq:
            cost, node, predecessor = heapq.heappop(pq)
            if node in distances:
                continue
            distances[node] = cost
            prev[node] = predecessor
            
            for neighbor in G[node]:
                if neighbor not in distances:
                    edge_data = G[node][neighbor]
                    heapq.heappush(pq, (cost + edge_data['cost'], neighbor, node))
        
        # For each destination, find the shortest path
        for dst in dsts:
            if dst not in distances:
                continue
                
            # Reconstruct path
            path_nodes = []
            current = dst
            while current is not None:
                path_nodes.append(current)
                current = prev.get(current)
            path_nodes.reverse()
            
            # Add edges to broadcast topology
            for i in range(len(path_nodes) - 1):
                u, v = path_nodes[i], path_nodes[i + 1]
                edge_data = G[u][v]
                bc_topology.append_dst_partition_path(dst, partition, [u, v, edge_data])
    
    return bc_topology

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import json
import networkx as nx
import itertools
import heapq
import math
from collections import defaultdict, deque

def load_network_from_config(config_file):
    """Load network graph from configuration file"""
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    G = nx.DiGraph()
    
    # We need the actual network topology
    # For now, create a simplified topology based on regions
    regions = [config['source_node']] + config['dest_nodes']
    for region in regions:
        G.add_node(region)
    
    # Add edges between all regions with reasonable defaults
    # In practice, this would come from actual network data
    for src in regions:
        for dst in regions:
            if src != dst:
                # Simple cost model: higher for cross-provider
                src_prov = src.split(':')[0]
                dst_prov = dst.split(':')[0]
                
                if src_prov == dst_prov:
                    # Intra-provider: low cost
                    cost = 0.02
                    throughput = 10.0
                else:
                    # Inter-provider: higher cost
                    cost = 0.10
                    throughput = 5.0
                
                G.add_edge(src, dst, cost=cost, throughput=throughput)
    
    return G, config

def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int):
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    
    # Provider-specific bandwidth limits (Gbps)
    # These will be multiplied by number of VMs in evaluation
    provider_limits = {
        'aws': {'ingress': 10, 'egress': 5},
        'gcp': {'ingress': 16, 'egress': 7},
        'azure': {'ingress': 16, 'egress': 16}
    }
    
    def get_provider(node):
        return node.split(':')[0] if ':' in node else 'unknown'
    
    # Phase 1: Find initial paths using cost-aware Dijkstra
    all_paths = {}
    path_costs = {}
    
    for dst in dsts:
        all_paths[dst] = []
        # Find k shortest paths for load balancing
        k = min(5, num_partitions)  # Up to 5 alternative paths
        
        try:
            # Use Yen's algorithm for k-shortest paths
            paths = list(itertools.islice(
                nx.shortest_simple_paths(G, src, dst, weight='cost'),
                k
            ))
        except nx.NetworkXNoPath:
            # Fallback to single shortest path
            try:
                paths = [nx.shortest_path(G, src, dst, weight='cost')]
            except:
                continue
        
        for path in paths:
            all_paths[dst].append(path)
            # Calculate path cost
            path_cost = 0
            for i in range(len(path) - 1):
                path_cost += G[path[i]][path[j]]['cost']
            path_costs[(dst, tuple(path))] = path_cost
    
    # Phase 2: Assign partitions to paths with load balancing
    # Group destinations by provider for better sharing
    dst_by_provider = defaultdict(list)
    for dst in dsts:
        dst_by_provider[get_provider(dst)].append(dst)
    
    # Calculate approximate flow distribution
    edge_load = defaultdict(int)
    node_in_degree = defaultdict(int)
    node_out_degree = defaultdict(int)
    
    # Initialize with one partition per destination on cheapest path
    for dst in dsts:
        if not all_paths[dst]:
            continue
        cheapest_path = min(all_paths[dst], key=lambda p: path_costs.get((dst, tuple(p)), float('inf')))
        for i in range(len(cheapest_path) - 1):
            u, v = cheapest_path[i], cheapest_path[i + 1]
            edge_load[(u, v)] += 1
            node_out_degree[u] += 1
            node_in_degree[v] += 1
    
    # Phase 3: Assign remaining partitions with load awareness
    for partition in range(num_partitions):
        for dst in dsts:
            if not all_paths[dst]:
                continue
            
            # Evaluate candidate paths considering current load
            best_score = float('inf')
            best_path = None
            
            for path in all_paths[dst]:
                # Calculate load impact score
                load_impact = 0
                path_cost = path_costs.get((dst, tuple(path)), 0)
                
                for i in range(len(path) - 1):
                    u, v = path[i], path[i + 1]
                    current_load = edge_load[(u, v)]
                    
                    # Estimate bandwidth constraint impact
                    u_provider = get_provider(u)
                    v_provider = get_provider(v)
                    
                    # Consider egress constraint at u
                    if node_out_degree[u] > 0:
                        egress_limit = provider_limits.get(u_provider, {}).get('egress', 5)
                        # Approximate per-edge throughput
                        per_edge_throughput = egress_limit / max(node_out_degree[u], 1)
                        # Penalize heavily loaded edges
                        load_impact += current_load / per_edge_throughput
                    
                    # Consider ingress constraint at v
                    if node_in_degree[v] > 0:
                        ingress_limit = provider_limits.get(v_provider, {}).get('ingress', 10)
                        per_edge_throughput = ingress_limit / max(node_in_degree[v], 1)
                        load_impact += current_load / per_edge_throughput
                
                # Combined score: cost + load impact
                score = path_cost * 0.7 + load_impact * 0.3
                
                if score < best_score:
                    best_score = score
                    best_path = path
            
            if best_path:
                # Update loads for chosen path
                for i in range(len(best_path) - 1):
                    u, v = best_path[i], best_path[i + 1]
                    edge_load[(u, v)] += 1
                    node_out_degree[u] += 1
                    node_in_degree[v] += 1
                
                # Record path in topology
                for i in range(len(best_path) - 1):
                    u, v = best_path[i], best_path[i + 1]
                    edge_data = G[u][v]
                    bc_topology.append_dst_partition_path(dst, partition, [u, v, edge_data])
    
    return bc_topology

# Main execution for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python algorithm.py <config_file>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    G, config = load_network_from_config(config_file)
    
    result = search_algorithm(
        config['source_node'],
        config['dest_nodes'],
        G,
        config['num_partitions']
    )
    
    # Print summary
    print(f"Source: {result.src}")
    print(f"Destinations: {len(result.dsts)}")
    print(f"Partitions: {result.num_partitions}")
    print("Paths assigned successfully")'''
        
        return {"code": code}