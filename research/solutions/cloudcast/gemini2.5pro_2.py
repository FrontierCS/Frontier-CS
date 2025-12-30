import networkx as nx
import random
import math
import inspect
import textwrap

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
    """
    Designs routing paths for broadcasting data partitions to multiple destinations.
    This algorithm uses an iterative local search approach to minimize total cost.
    1.  Initial Solution: For each destination, k diverse paths are found, and partitions are
        distributed among them in a round-robin fashion to encourage load balancing.
    2.  Iterative Improvement: The algorithm then iteratively identifies the main bottleneck
        (the edge causing the longest transfer time) and attempts to reroute one of the
        partitions using that edge to an alternative, cheaper path.
    3.  Cost Model: A detailed cost model, incorporating both egress and instance costs,
        is used to evaluate each potential change. The instance cost is sensitive to the
        total transfer time, which depends on network congestion.
    4.  Termination: The process repeats for a fixed number of iterations, gradually
        improving the solution by mitigating bottlenecks.
    """

    class Optimizer:
        def __init__(self, src, dsts, G, num_partitions):
            self.src = src
            self.dsts = dsts
            self.G = G
            self.num_partitions = int(num_partitions)

            # Constants from the problem spec
            self.num_vms = 2
            self.instance_rate_hr = 0.54
            self.ingress_limit = {"aws": 10, "gcp": 16, "azure": 16}
            self.egress_limit = {"aws": 5, "gcp": 7, "azure": 16}

            # s_partition is a common scaling factor in the cost function, so its
            # absolute value doesn't affect the optimization. We can set it to 1.
            self.s_partition = 1.0

            self.topology = BroadCastTopology(src, dsts, num_partitions)
            # Internal representation of paths using node lists for easier manipulation
            self.paths = {dst: {p: [] for p in range(self.num_partitions)} for dst in dsts}

        def _get_path_edges(self, node_path: list):
            """Converts a list of nodes to a list of edges with data."""
            if not node_path or len(node_path) < 2:
                return []
            edges = []
            for i in range(len(node_path) - 1):
                u, v = node_path[i], node_path[i + 1]
                if self.G.has_edge(u, v):
                    edges.append([u, v, self.G[u][v]])
            return edges

        def _calculate_cost(self):
            """Calculates the total cost of the current topology."""
            edge_partition_counts = {}
            nodes_used = {self.src}

            for dst in self.dsts:
                for p in range(self.num_partitions):
                    node_path = self.paths[dst][p]
                    for i in range(len(node_path) - 1):
                        u, v = node_path[i], node_path[i + 1]
                        edge = (u, v)
                        edge_partition_counts[edge] = edge_partition_counts.get(edge, 0) + 1
                        nodes_used.add(u)
                        nodes_used.add(v)

            if not edge_partition_counts:
                return float('inf'), None

            # 1. Egress Cost
            c_egress = sum(
                count * self.s_partition * self.G[u][v]['cost']
                for (u, v), count in edge_partition_counts.items()
            )

            # 2. Transfer Time
            # 2a. Calculate actual throughput f_e for each used edge
            used_egress_edges = {node: [] for node in nodes_used}
            used_ingress_edges = {node: [] for node in nodes_used}
            for u, v in edge_partition_counts.keys():
                used_egress_edges[u].append((u, v))
                used_ingress_edges[v].append((u, v))

            actual_throughputs = {}
            for u, v in edge_partition_counts.keys():
                provider_u = u.split(':')[0]
                provider_v = v.split(':')[0]

                egress_limit = self.egress_limit.get(provider_u, float('inf')) * self.num_vms
                ingress_limit = self.ingress_limit.get(provider_v, float('inf')) * self.num_vms

                num_egress_at_u = len(used_egress_edges[u])
                num_ingress_at_v = len(used_ingress_edges[v])

                throttled_egress = egress_limit / num_egress_at_u if num_egress_at_u > 0 else float('inf')
                throttled_ingress = ingress_limit / num_ingress_at_v if num_ingress_at_v > 0 else float('inf')

                actual_throughputs[(u, v)] = min(self.G[u][v]['throughput'], throttled_egress, throttled_ingress)

            # 2b. Find the maximum transfer time (bottleneck)
            t_transfer = 0.0
            bottleneck_edge = None
            for (u, v), count in edge_partition_counts.items():
                data_on_edge_Gb = count * self.s_partition * 8
                f_e = actual_throughputs.get((u, v), 1e-9)
                time_on_edge = data_on_edge_Gb / f_e if f_e > 0 else float('inf')
                if time_on_edge > t_transfer:
                    t_transfer = time_on_edge
                    bottleneck_edge = (u, v)

            # 3. Instance Cost
            v_count = len(nodes_used)
            c_instance = v_count * self.num_vms * (self.instance_rate_hr / 3600) * t_transfer

            total_cost = c_egress + c_instance
            return total_cost, bottleneck_edge

        def _find_k_diverse_paths(self, src_node, dst_node, k):
            """Finds k diverse paths using a weight-penalizing heuristic."""
            paths = []
            temp_G = self.G.copy()
            for _ in range(k):
                try:
                    path = nx.dijkstra_path(temp_G, src_node, dst_node, weight='cost')
                    paths.append(path)
                    for i in range(len(path) - 1):
                        u, v = path[i], path[i + 1]
                        temp_G[u][v]['cost'] *= 1.5
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    break
            if not paths:
                try:
                    path = nx.dijkstra_path(self.G, src_node, dst_node, weight='cost')
                    paths.append(path)
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    pass
            return paths

        def run(self):
            # 1. Initial Assignment: Round-robin partitions over k diverse paths.
            k = min(self.num_partitions, 5)
            for dst in self.dsts:
                diverse_paths = self._find_k_diverse_paths(self.src, dst, k)
                if not diverse_paths: continue
                for p in range(self.num_partitions):
                    self.paths[dst][p] = diverse_paths[p % len(diverse_paths)]

            # 2. Iterative Improvement (Local Search)
            # Iterations scale with problem size, with a cap
            num_iterations = min(500, max(100, (self.num_partitions * len(self.dsts))))
            
            current_cost, bottleneck_edge = self._calculate_cost()

            for _ in range(num_iterations):
                if bottleneck_edge is None:
                    break

                # Find all (dst, partition) pairs using the bottleneck edge
                candidates = []
                u_b, v_b = bottleneck_edge
                for dst_cand in self.dsts:
                    for p_cand in range(self.num_partitions):
                        path = self.paths[dst_cand][p_cand]
                        if any(path[j] == u_b and path[j + 1] == v_b for j in range(len(path) - 1)):
                            candidates.append((dst_cand, p_cand))
                
                if not candidates: break
                
                # Select a random candidate to reroute
                dst_to_reroute, p_to_reroute = random.choice(candidates)
                original_path = self.paths[dst_to_reroute][p_to_reroute]
                
                # Find an alternative path, heavily penalizing the bottleneck
                temp_G = self.G.copy()
                temp_G[u_b][v_b]['cost'] *= 10
                try:
                    new_path = nx.dijkstra_path(temp_G, self.src, dst_to_reroute, weight='cost')
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    continue

                # Evaluate the move (hill climbing)
                self.paths[dst_to_reroute][p_to_reroute] = new_path
                new_cost, new_bottleneck = self._calculate_cost()

                if new_cost < current_cost:
                    current_cost = new_cost
                    bottleneck_edge = new_bottleneck
                else:
                    self.paths[dst_to_reroute][p_to_reroute] = original_path

            # 3. Finalize BroadCastTopology object with the best found paths
            for dst in self.dsts:
                for p in range(self.num_partitions):
                    node_path = self.paths[dst][p]
                    edge_path = self._get_path_edges(node_path)
                    self.topology.set_dst_partition_paths(dst, p, edge_path)

            return self.topology

    if num_partitions == 0 or not dsts:
        return BroadCastTopology(src, dsts, num_partitions)

    optimizer = Optimizer(src, dsts, G, num_partitions)
    return optimizer.run()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns the Python code for the search algorithm as a string.
        """
        # Get the source code of the required functions and classes
        broadcast_topology_code = inspect.getsource(BroadCastTopology)
        search_algorithm_code = inspect.getsource(search_algorithm)

        # Combine them into a single code string
        full_code = textwrap.dedent(f"""
        import networkx as nx
        import random
        import math

        {broadcast_topology_code}

        {search_algorithm_code}
        """)

        return {"code": full_code}