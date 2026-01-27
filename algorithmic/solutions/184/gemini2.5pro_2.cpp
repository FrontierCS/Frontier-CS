#include <iostream>
#include <vector>
#include <algorithm>
#include <set>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N, M;
    std::cin >> N >> M;

    std::vector<std::vector<int>> adj(N + 1);
    std::vector<int> current_degree(N + 1);

    // Use a temporary std::set to handle multiple edges cleanly and build adjacency lists.
    // The scope block ensures adj_set is freed after use.
    {
        std::vector<std::set<int>> adj_set(N + 1);
        for (int i = 0; i < M; ++i) {
            int u, v;
            std::cin >> u >> v;
            adj_set[u].insert(v);
            adj_set[v].insert(u);
        }

        for (int i = 1; i <= N; ++i) {
            adj[i].assign(adj_set[i].begin(), adj_set[i].end());
            current_degree[i] = static_cast<int>(adj[i].size());
        }
    }

    std::vector<bool> removed(N + 1, false);
    std::vector<int> solution_set;
    int num_removed = 0;

    while (num_removed < N) {
        int min_deg_v = -1;
        int min_deg = N + 1;

        // Find a non-removed vertex with the minimum current degree.
        // Tie-breaking is done by picking the vertex with the smallest index.
        for (int i = 1; i <= N; ++i) {
            if (!removed[i] && current_degree[i] < min_deg) {
                min_deg = current_degree[i];
                min_deg_v = i;
            }
        }
        
        if (min_deg_v == -1) {
            // All remaining vertices have been processed.
            break;
        }

        // Add the selected vertex to our independent set.
        solution_set.push_back(min_deg_v);
        
        // Collect vertices to be removed: the selected vertex and its neighbors.
        std::vector<int> to_remove_this_step;
        if (!removed[min_deg_v]) {
            to_remove_this_step.push_back(min_deg_v);
        }
        for(int neighbor : adj[min_deg_v]) {
            if (!removed[neighbor]) {
                to_remove_this_step.push_back(neighbor);
            }
        }

        // Process removals and update degrees.
        for (int u : to_remove_this_step) {
            if (!removed[u]) {
                removed[u] = true;
                num_removed++;
                // For each removed vertex, decrement the degree of its non-removed neighbors.
                for (int v_neighbor : adj[u]) {
                    if (!removed[v_neighbor]) {
                        current_degree[v_neighbor]--;
                    }
                }
            }
        }
    }

    // Prepare the final output array.
    std::vector<int> output(N + 1, 0);
    for (int v : solution_set) {
        output[v] = 1;
    }

    for (int i = 1; i <= N; ++i) {
        std::cout << output[i] << "\n";
    }

    return 0;
}