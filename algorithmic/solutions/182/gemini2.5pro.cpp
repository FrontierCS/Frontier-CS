#include <iostream>
#include <vector>
#include <algorithm>
#include <list>
#include <chrono>
#include <random>
#include <utility>

// Global variables
int N_nodes, M_edges;
std::vector<std::vector<int>> adj;
std::vector<bool> in_vc;
std::vector<int> initial_degree;
std::mt19937 rng;

// Function to read input, handle duplicate edges, and build the graph
void read_input_and_build_graph() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(nullptr);

    std::cin >> N_nodes >> M_edges;

    std::vector<std::pair<int, int>> edges;
    edges.reserve(M_edges);
    for (int i = 0; i < M_edges; ++i) {
        int u, v;
        std::cin >> u >> v;
        if (u > v) std::swap(u, v);
        edges.push_back({u, v});
    }

    std::sort(edges.begin(), edges.end());
    edges.erase(std::unique(edges.begin(), edges.end()), edges.end());

    adj.resize(N_nodes + 1);
    initial_degree.assign(N_nodes + 1, 0);
    M_edges = edges.size();

    for (const auto& edge : edges) {
        adj[edge.first].push_back(edge.second);
        adj[edge.second].push_back(edge.first);
        initial_degree[edge.first]++;
        initial_degree[edge.second]++;
    }
}

// Generates an initial vertex cover using a greedy max-degree heuristic
void solve_greedy_max_degree() {
    in_vc.assign(N_nodes + 1, false);
    std::vector<int> current_degree = initial_degree;
    if (M_edges == 0) return;

    std::vector<std::list<int>> buckets(N_nodes);
    std::vector<std::list<int>::iterator> pos_in_bucket(N_nodes + 1);
    int max_degree = 0;

    for (int i = 1; i <= N_nodes; ++i) {
        buckets[current_degree[i]].push_front(i);
        pos_in_bucket[i] = buckets[current_degree[i]].begin();
        if (current_degree[i] > max_degree) {
            max_degree = current_degree[i];
        }
    }

    while (max_degree > 0) {
        while (max_degree > 0 && buckets[max_degree].empty()) {
            max_degree--;
        }
        if (max_degree == 0) break;

        int u = buckets[max_degree].front();
        
        in_vc[u] = true;
        buckets[current_degree[u]].erase(pos_in_bucket[u]);
        current_degree[u] = 0;

        for (int v : adj[u]) {
            if (current_degree[v] > 0) {
                buckets[current_degree[v]].erase(pos_in_bucket[v]);
                current_degree[v]--;
                buckets[current_degree[v]].push_front(v);
                pos_in_bucket[v] = buckets[current_degree[v]].begin();
            }
        }
    }
}

// Improves the solution using local search
void local_search() {
    auto start_time = std::chrono::high_resolution_clock::now();
    double time_limit = 1.8;

    std::vector<int> vc_nodes;
    for (int i = 1; i <= N_nodes; ++i) {
        if (in_vc[i]) {
            vc_nodes.push_back(i);
        }
    }

    bool improved = true;
    while(improved) {
        auto current_time = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = current_time - start_time;
        if (elapsed.count() > time_limit) break;

        improved = false;

        // Phase 1: Redundancy removal (1-for-0 moves)
        std::shuffle(vc_nodes.begin(), vc_nodes.end(), rng);
        std::vector<int> next_vc_nodes;
        next_vc_nodes.reserve(vc_nodes.size());

        for (int u : vc_nodes) {
            bool redundant = true;
            for (int v : adj[u]) {
                if (!in_vc[v]) {
                    redundant = false;
                    break;
                }
            }
            if (redundant) {
                in_vc[u] = false;
                improved = true;
            } else {
                next_vc_nodes.push_back(u);
            }
        }
        vc_nodes = next_vc_nodes;
        if (improved) continue;
        
        // Phase 2: 2-for-1 swaps
        std::shuffle(vc_nodes.begin(), vc_nodes.end(), rng);
        bool swap_done = false;
        for (int v1 : vc_nodes) {
            if (!in_vc[v1]) continue;

            std::vector<int> uncovered_neighbors_v1;
            for (int neighbor : adj[v1]) {
                if (!in_vc[neighbor]) {
                    uncovered_neighbors_v1.push_back(neighbor);
                }
            }

            if (uncovered_neighbors_v1.size() == 1) {
                int u = uncovered_neighbors_v1[0];
                if (in_vc[u]) continue;
                
                for (int v2 : adj[u]) {
                    if (v2 != v1 && in_vc[v2]) {
                        bool v2_ok = true;
                        for (int neighbor_of_v2 : adj[v2]) {
                            if (!in_vc[neighbor_of_v2] && neighbor_of_v2 != u) {
                                v2_ok = false;
                                break;
                            }
                        }
                        if (v2_ok) {
                            bool is_adj = false;
                            int v_small_deg = v1, v_large_deg = v2;
                            if (adj[v_small_deg].size() > adj[v_large_deg].size()) {
                                std::swap(v_small_deg, v_large_deg);
                            }
                            for (int neighbor : adj[v_small_deg]) {
                                if (neighbor == v_large_deg) {
                                    is_adj = true;
                                    break;
                                }
                            }

                            if (!is_adj) {
                                in_vc[v1] = false;
                                in_vc[v2] = false;
                                in_vc[u] = true;
                                improved = true;
                                swap_done = true;
                                break;
                            }
                        }
                    }
                }
            }
            if (swap_done) break;
        }
        if (swap_done) {
            vc_nodes.clear();
            for (int i = 1; i <= N_nodes; ++i) if (in_vc[i]) vc_nodes.push_back(i);
        }
    }
}

void print_output() {
    for (int i = 1; i <= N_nodes; ++i) {
        std::cout << in_vc[i] << "\n";
    }
}

int main() {
    rng.seed(std::chrono::steady_clock::now().time_since_epoch().count());
    read_input_and_build_graph();
    solve_greedy_max_degree();
    local_search();
    print_output();
    return 0;
}