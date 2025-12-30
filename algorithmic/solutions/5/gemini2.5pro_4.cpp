#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

void solve() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, m;
    std::cin >> n >> m;

    // Scoring parameters are not used in the logic.
    std::vector<int> a(10);
    for (int i = 0; i < 10; ++i) {
        std::cin >> a[i];
    }

    std::vector<std::vector<int>> adj(n + 1);
    std::vector<int> out_degree(n + 1, 0);
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        out_degree[u]++;
    }

    // Sort adjacency lists by neighbor's out-degree in descending order.
    // This pre-computation speeds up the greedy choice in each step.
    for (int i = 1; i <= n; ++i) {
        std::sort(adj[i].begin(), adj[i].end(), [&](int u, int v) {
            return out_degree[u] > out_degree[v];
        });
    }

    std::vector<int> best_path;
    
    // Generate a random permutation of vertices to use as starting nodes.
    std::vector<int> start_nodes(n);
    std::iota(start_nodes.begin(), start_nodes.end(), 1);
    
    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    std::shuffle(start_nodes.begin(), start_nodes.end(), rng);

    // Use a marker technique for efficient 'visited' checks across multiple runs.
    std::vector<int> visited_marker(n + 1, 0);
    int run_id = 0;

    auto start_time = std::chrono::steady_clock::now();
    
    for (int start_node : start_nodes) {
        // Stop if we approach the time limit.
        auto current_time = std::chrono::steady_clock::now();
        if (std::chrono::duration_cast<std::chrono::milliseconds>(current_time - start_time).count() > 3800) {
            break;
        }

        // If a Hamiltonian path is found, we can stop.
        if (best_path.size() == n) {
            break;
        }

        run_id++;
        std::vector<int> current_path;
        current_path.reserve(n);

        int current_node = start_node;
        current_path.push_back(current_node);
        visited_marker[current_node] = run_id;

        while (true) {
            int first_unvisited_idx = -1;
            // Find the first unvisited neighbor in the sorted adjacency list.
            for (size_t i = 0; i < adj[current_node].size(); ++i) {
                if (visited_marker[adj[current_node][i]] != run_id) {
                    first_unvisited_idx = i;
                    break;
                }
            }
            
            if (first_unvisited_idx == -1) {
                break; // No unvisited neighbors, path is stuck.
            }

            // Collect all unvisited neighbors with the same maximum out-degree for random tie-breaking.
            int max_deg = out_degree[adj[current_node][first_unvisited_idx]];
            int last_candidate_idx = first_unvisited_idx;
            for (size_t i = first_unvisited_idx + 1; i < adj[current_node].size(); ++i) {
                int neighbor = adj[current_node][i];
                if (visited_marker[neighbor] != run_id && out_degree[neighbor] == max_deg) {
                    last_candidate_idx = i;
                } else {
                    break;
                }
            }

            // Randomly pick one of the best candidates.
            int choice_range_size = last_candidate_idx - first_unvisited_idx + 1;
            int choice_offset = rng() % choice_range_size;
            int choice_idx = first_unvisited_idx + choice_offset;
            
            current_node = adj[current_node][choice_idx];
            current_path.push_back(current_node);
            visited_marker[current_node] = run_id;
        }

        // Update the best path if the current one is longer.
        if (current_path.size() > best_path.size()) {
            best_path = current_path;
        }
    }
    
    if (best_path.empty() && n > 0) {
        best_path.push_back(1);
    }

    std::cout << best_path.size() << "\n";
    for (size_t i = 0; i < best_path.size(); ++i) {
        std::cout << best_path[i] << (i == best_path.size() - 1 ? "" : " ");
    }
    std::cout << "\n";
}

int main() {
    solve();
    return 0;
}