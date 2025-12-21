import networkx as nx

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import networkx as nx

class BroadCastTopology:
    def __init__(self, src: str, dsts: list[str], num_partitions: int):
        self.src = src
        self.dsts = dsts
        self.num_partitions = int(num_partitions)
        # Structure: {dst: {partition_id: [edges]}}
        # Each edge is [src_node, dst_node, edge_data_dict]
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
    # Heuristic Strategy:
    # 1. Goal: Minimize Total Cost = Egress Cost + Instance Cost.
    # 2. Egress Cost is minimized by a Steiner Tree (minimizing sum of edge costs).
    # 3. Instance Cost depends on transfer time (bottleneck bandwidth) and number of active nodes.
    # 4. We approximate the Minimum Steiner Tree using the Shortest Path Heuristic (Mehlhorn approx).
    # 5. To account for transfer time, we use a custom weight function that penalizes low-bandwidth edges.
    # 6. We use the *same* tree for all partitions to maximize multicast/broadcast efficiency (counting edge usage once per partition set).

    def heuristic_weight(u, v, d):
        # Base cost ($/GB)
        cost = d.get("cost", 0.0)
        # Throughput (Gbps)
        throughput = d.get("throughput", 1.0)
        # Avoid division by zero
        if throughput < 0.001: throughput = 0.001
        
        # Weight formula: Cost + (Factor / Throughput)
        # Factor 0.05 is chosen based on ratio of Instance_Rate ($0.54/h) to Data Volume/Time unit 
        # to balance egress savings vs speed.
        return cost + (0.05 / throughput)

    # Clean destination list
    unique_dsts = set(dsts)
    if src in unique_dsts:
        unique_dsts.remove(src)
    
    # Precompute all-pairs shortest paths using custom weight
    # This allows fast selection of the "closest" next node to add to the Steiner Tree
    try:
        paths_map = dict(nx.all_pairs_dijkstra_path(G, weight=heuristic_weight))
        dists_map = dict(nx.all_pairs_dijkstra_path_length(G, weight=heuristic_weight))
    except:
        # Fallback to pure cost
        paths_map = dict(nx.all_pairs_dijkstra_path(G, weight="cost"))
        dists_map = dict(nx.all_pairs_dijkstra_path_length(G, weight="cost"))

    # Initialize Tree with Source
    tree_nodes = {src}
    tree_graph = nx.DiGraph()
    tree_graph.add_node(src)
    
    remaining_dsts = set(unique_dsts)

    # Iteratively expand the tree
    while remaining_dsts:
        best_u, best_v, min_dist = None, None, float('inf')
        
        # Find the node v in remaining_dsts closest to any node u in current tree
        for u in tree_nodes:
            if u in dists_map:
                for v in remaining_dsts:
                    if v in dists_map[u]:
                        dist = dists_map[u][v]
                        if dist < min_dist:
                            min_dist = dist
                            best_u = u
                            best_v = v
        
        if best_u is None:
            # Cannot reach remaining destinations
            break
            
        # Add path from best_u to best_v to the tree
        path_nodes = paths_map[best_u][best_v]
        for i in range(len(path_nodes) - 1):
            u_seg, v_seg = path_nodes[i], path_nodes[i+1]
            if not tree_graph.has_edge(u_seg, v_seg):
                tree_graph.add_edge(u_seg, v_seg, **G[u_seg][v_seg])
                tree_nodes.add(u_seg)
                tree_nodes.add(v_seg)
        
        # Update remaining destinations
        # Remove any destination that is now part of the tree
        covered = [d for d in remaining_dsts if d in tree_nodes]
        for d in covered:
            remaining_dsts.remove(d)

    # Construct the topology object
    topology = BroadCastTopology(src, dsts, num_partitions)
    
    for dst in unique_dsts:
        path_edges = []
        try:
            # Extract the unique path in the tree
            tree_path = nx.shortest_path(tree_graph, src, dst)
            for i in range(len(tree_path) - 1):
                u, v = tree_path[i], tree_path[i+1]
                path_edges.append([u, v, tree_graph[u][v]])
        except (nx.NetworkXNoPath, KeyError):
            # Fallback to direct shortest path in G if tree is incomplete
            try:
                direct_path = nx.shortest_path(G, src, dst, weight="cost")
                for i in range(len(direct_path) - 1):
                    u, v = direct_path[i], direct_path[i+1]
                    path_edges.append([u, v, G[u][v]])
            except:
                continue

        # Assign the calculated path to all partitions
        # Using the same path maximizes multicast benefits
        for p in range(num_partitions):
            topology.set_dst_partition_paths(dst, p, path_edges)

    return topology
"""
        return {"code": code}
