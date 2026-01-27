#include <iostream>
#include <vector>
#include <algorithm>
#include <bitset>

// Using 1-based indexing for vertices, so size is N+1, up to 1000.
const int MAXN = 1001;

int N, M;
// Adjacency matrix using bitsets for fast set operations.
std::bitset<MAXN> adj[MAXN];
// Store vertex degrees for sorting heuristic.
int deg[MAXN];
// Permutation of vertices, to be sorted by degree.
std::vector<int> p;

// Store the best clique found so far.
std::bitset<MAXN> best_clique_mask;
size_t best_clique_size = 0;

void solve() {
    std::cin >> N >> M;
    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u][v] = 1;
        adj[v][u] = 1;
    }

    // Calculate initial degrees and create a list of all vertices.
    for (int i = 1; i <= N; ++i) {
        deg[i] = adj[i].count();
        p.push_back(i);
    }
    
    // Sort vertices by degree in descending order. This is a crucial heuristic
    // to explore more promising vertices first.
    std::sort(p.begin(), p.end(), [&](int u, int v) {
        return deg[u] > deg[v];
    });

    // Iterate through each vertex as a potential starting point for a clique.
    // The order is determined by the degree-sorted permutation `p`.
    for (int i = 0; i < N; ++i) {
        int u = p[i];

        // Pruning: The size of any clique containing `u` is at most `deg[u] + 1`.
        // If this upper bound is not better than the best clique found so far, we can stop.
        // Since vertices are sorted by decreasing degree, all subsequent vertices will also fail this check.
        if (deg[u] + 1 <= best_clique_size) {
            break;
        }

        std::bitset<MAXN> current_clique_mask;
        current_clique_mask[u] = 1;
        
        // Greedily build a clique starting with `u`.
        // Candidates for extending the clique are vertices that appear after `u` in the sorted list `p`.
        // This strategy avoids re-generating the same cliques and provides a good order for greedy choices.
        for (int j = i + 1; j < N; ++j) {
            int v = p[j];
            
            // Check if vertex `v` is connected to all vertices already in the current clique.
            // This is equivalent to checking if the current clique is a subset of `v`'s neighbors.
            // With bitsets, this check is very efficient.
            if ((current_clique_mask & adj[v]) == current_clique_mask) {
                current_clique_mask[v] = 1;
            }
        }
        
        size_t current_clique_size = current_clique_mask.count();
        if (current_clique_size > best_clique_size) {
            best_clique_size = current_clique_size;
            best_clique_mask = current_clique_mask;
        }
    }
    
    // Output the result in the required format: N lines of 0 or 1.
    for (int i = 1; i <= N; ++i) {
        std::cout << best_clique_mask[i] << "\n";
    }
}

int main() {
    // Fast I/O for competitive programming.
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    solve();
    
    return 0;
}