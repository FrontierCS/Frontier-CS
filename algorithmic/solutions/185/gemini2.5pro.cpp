#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <bitset>

// Fast I/O
void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

const int MAXN = 1001; // Max N is 1000, vertices are 1-indexed
int N, M;
std::bitset<MAXN> adj[MAXN];
int degree[MAXN] = {0};

int main() {
    fast_io();

    std::cin >> N >> M;
    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        // Handle multiple edges by only processing the first one
        if (!adj[u][v]) {
            adj[u][v] = 1;
            adj[v][u] = 1;
            degree[u]++;
            degree[v]++;
        }
    }

    // Create a permutation of vertices from 1 to N
    std::vector<int> p(N);
    std::iota(p.begin(), p.end(), 1);

    // Sort vertices by degree in descending order. This is a crucial heuristic.
    std::sort(p.begin(), p.end(), [&](int u, int v) {
        return degree[u] > degree[v];
    });

    std::vector<int> max_clique;

    // Iterate through each vertex as a potential starting node for a clique
    for (int i = 0; i < N; ++i) {
        int start_node = p[i];

        // Pruning: if the maximum possible clique size from this start_node
        // (which is its degree + 1) is not greater than the current best, skip it.
        if (degree[start_node] + 1 <= max_clique.size()) {
            continue;
        }

        std::vector<int> current_clique_vec;
        current_clique_vec.reserve(degree[start_node] + 1);
        current_clique_vec.push_back(start_node);
        
        std::bitset<MAXN> current_clique_bs;
        current_clique_bs[start_node] = 1;
        
        // Greedily build a clique starting with start_node.
        // Candidates are neighbors of start_node that appear later in the sorted permutation.
        // We iterate through them in the pre-sorted (by degree) order.
        for (int j = i + 1; j < N; ++j) {
            int u = p[j];

            if (adj[start_node][u]) {
                // Check if u is connected to all vertices already in the current clique.
                // This is efficient with bitsets.
                if ((adj[u] & current_clique_bs) == current_clique_bs) {
                    current_clique_vec.push_back(u);
                    current_clique_bs[u] = 1;
                }
            }
        }
        
        if (current_clique_vec.size() > max_clique.size()) {
            max_clique = current_clique_vec;
        }
    }

    // Prepare output in the required format
    std::vector<bool> in_clique(N + 1, false);
    for (int node : max_clique) {
        in_clique[node] = true;
    }

    for (int i = 1; i <= N; ++i) {
        std::cout << in_clique[i] << "\n";
    }

    return 0;
}