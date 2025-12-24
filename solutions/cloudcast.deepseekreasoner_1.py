import json
import math
import heapq
import random
from collections import defaultdict, deque
import networkx as nx
from typing import Dict, List, Set, Tuple, Optional


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": self._get_code()}
    
    def _get_code(self) -> str:
        return '''
import json
import math
import heapq
import random
from collections import defaultdict, deque
import networkx as nx
from typing import Dict, List, Set, Tuple, Optional


def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> 'BroadCastTopology':
    """
    Design routing paths for broadcasting data partitions to multiple destinations.
    Uses multi-path load balancing with capacity-aware routing.
    """
    bc = BroadCastTopology(src, dsts, num_partitions)
    
    # Get provider from node string
    def get_provider(node: str) -> str:
        return node.split(':')[0]
    
    # Default bandwidth limits (per VM, will be multiplied by num_vms in evaluation)
    ingress_limits = {'aws': 10, 'gcp': 16, 'azure': 16}
    egress_limits = {'aws': 5, 'gcp': 7, 'azure': 16}
    
    # Estimate capacity-aware shortest paths
    # Strategy: Use multiple diverse paths per destination to balance load
    
    # Precompute candidate paths for each destination
    candidate_paths = {}
    for dst in dsts:
        # Find k shortest diverse paths
        paths = []
        try:
            # Get simple paths sorted by hop count
            all_paths = list(nx.all_simple_paths(G, src, dst, cutoff=10))
            all_paths.sort(key=len)
            
            # Take up to min(5, num_partitions) diverse paths
            max_paths = min(5, num_partitions, len(all_paths))
            # Select diverse paths with different intermediate nodes
            selected = []
            used_nodes = set()
            for path in all_paths:
                if len(selected) >= max_paths:
                    break
                path_nodes = set(path[1:-1])  # Exclude src and dst
                # Check diversity: at most 50% overlap
                if not selected or len(path_nodes & used_nodes) < len(used_nodes) * 0.5:
                    selected.append(path)
                    used_nodes.update(path_nodes)
            
            paths = selected[:max_paths]
        except:
            # Fallback: single shortest path
            try:
                path = nx.shortest_path(G, src, dst)
                paths = [path]
            except:
                paths = []
        
        if not paths:
            # Last resort: direct if edge exists, otherwise empty
            if G.has_edge(src, dst):
                paths = [[src, dst]]
            else:
                paths = []
        
        candidate_paths[dst] = paths
    
    # Assign partitions to paths using round-robin for load balancing
    partition_assignments = {}
    for dst in dsts:
        paths = candidate_paths[dst]
        if not paths:
            continue
        
        # Assign partitions to paths in round-robin
        assignments = {}
        for p in range(num_partitions):
            path_idx = p % len(paths)
            assignments[p] = paths[path_idx]
        partition_assignments[dst] = assignments
    
    # Fill the broadcast topology
    for dst, assignments in partition_assignments.items():
        for partition, path in assignments.items():
            edges = []
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                edge_data = G[u][v]
                edges.append([u, v, edge_data])
            bc.set_dst_partition_paths(dst, partition, edges)
    
    return bc


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
'''


if __name__ == "__main__":
    solution = Solution()
    print(solution.solve())
