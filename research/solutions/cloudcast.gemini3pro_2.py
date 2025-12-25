import networkx as nx

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        # Returns the algorithm code as a string to be executed by the evaluator
        algorithm_code = r"""import networkx as nx
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
    Implements a Steiner Tree approximation (Takahashi-Matsuyama heuristic) to minimize 
    total egress cost while respecting basic throughput constraints.
    """
    
    # 1. Pre-process Graph: Filter out edges with extremely low throughput
    # to prevent instance cost blowout due to bottlenecks.
    valid_edges = []
    min_throughput = 0.05 # Gbps threshold
    
    for u, v, data in G.edges(data=True):
        if data.get('throughput', 0.0) >= min_throughput:
            valid_edges.append((u, v, data))
            
    SG = nx.DiGraph()
    SG.add_edges_from(valid_edges)
    
    # 2. Build Broadcast Tree
    # Start with source, iteratively connect closest remaining destination to the tree.
    tree_nodes = {src}
    tree_edges = set()
    
    remaining_dsts = set(dsts)
    if src in remaining_dsts:
        remaining_dsts.remove(src)
        
    # If source is effectively isolated in SG, logic will fail gracefully to fallback
    if src in SG:
        while remaining_dsts:
            try:
                # Multi-source Dijkstra: find shortest paths from ALL tree nodes to ALL other nodes
                dists, paths = nx.multi_source_dijkstra(SG, sources=list(tree_nodes), weight='cost')
                
                # Find the closest reachable destination not yet in tree
                best_dst = None
                min_dist = float('inf')
                
                reachable = [d for d in remaining_dsts if d in dists]
                if not reachable:
                    break
                    
                for d in reachable:
                    if dists[d] < min_dist:
                        min_dist = dists[d]
                        best_dst = d
                
                if best_dst:
                    # Add path to the tree
                    path = paths[best_dst]
                    for i in range(len(path) - 1):
                        u, v = path[i], path[i+1]
                        tree_edges.add((u, v))
                        tree_nodes.add(u)
                        tree_nodes.add(v)
                    
                    # Remove covered destinations
                    for node in path:
                        if node in remaining_dsts:
                            remaining_dsts.remove(node)
                else:
                    break
            except Exception:
                break
    
    # Construct a graph from the tree edges to easily extract paths
    tree_graph = nx.DiGraph()
    for u, v in tree_edges:
        if SG.has_edge(u, v):
            tree_graph.add_edge(u, v, **SG[u][v])
        elif G.has_edge(u, v):
            tree_graph.add_edge(u, v, **G[u][v])

    # 3. Assign Paths to Topology
    topology = BroadCastTopology(src, dsts, num_partitions)
    
    for dst in dsts:
        if dst == src:
            continue
        
        final_path_edges = []
        path_found = False
        
        # Priority 1: Use the Steiner Tree path (maximizes edge sharing -> minimizes egress cost)
        try:
            nodes = nx.shortest_path(tree_graph, src, dst)
            for i in range(len(nodes) - 1):
                u, v = nodes[i], nodes[i+1]
                final_path_edges.append([u, v, tree_graph[u][v]])
            path_found = True
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            # Priority 2: Direct Shortest Path on Clean Graph (minimize cost, avoid bottlenecks)
            try:
                nodes = nx.shortest_path(SG, src, dst, weight='cost')
                for i in range(len(nodes) - 1):
                    u, v = nodes[i], nodes[i+1]
                    final_path_edges.append([u, v, SG[u][v]])
                path_found = True
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                # Priority 3: Direct Shortest Path on Original Graph (last resort)
                try:
                    nodes = nx.shortest_path(G, src, dst, weight='cost')
                    for i in range(len(nodes) - 1):
                        u, v = nodes[i], nodes[i+1]
                        final_path_edges.append([u, v, G[u][v]])
                    path_found = True
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    pass
        
        if path_found:
            # Assign the same optimized path to all partitions to maximize shared egress savings
            for p in range(num_partitions):
                topology.set_dst_partition_paths(dst, p, final_path_edges)

    return topology
"""
        return {"code": algorithm_code}
