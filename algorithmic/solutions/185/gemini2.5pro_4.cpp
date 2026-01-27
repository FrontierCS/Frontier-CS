#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <bitset>

// Set a constant for the maximum number of vertices.
// The problem statement says N <= 1000, so 1001 is safe for 1-based indexing.
const int MAXN = 1001;

// Global variables for graph representation.
int N, M;
// Adjacency matrix using bitsets for efficient set operations.
std::vector<std::bitset<MAXN>> adj_mat;

// The main logic of the solution.
void solve() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // Read graph size
    std::cin >> N >> M;
    adj_mat.resize(N + 1);

    // Using a temporary boolean matrix to handle multiple edges easily.
    // This is fine for N <= 1000 as it's about 1MB.
    std::vector<std::vector<bool>> temp_adj(N + 1, std::vector<bool>(N + 1, false));
    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        if (u == v) continue;
        temp_adj[u][v] = true;
        temp_adj[v][u] = true;
    }

    // Adjacency list for efficient neighbor iteration during degeneracy order calculation.
    std::vector<std::vector<int>> adj_list(N + 1);
    // Populate bitset adjacency matrix and adjacency list from the temporary matrix.
    for (int i = 1; i <= N; ++i) {
        for (int j = i + 1; j <= N; ++j) {
            if (temp_adj[i][j]) {
                adj_mat[i][j] = adj_mat[j][i] = 1;
                adj_list[i].push_back(j);
                adj_list[j].push_back(i);
            }
        }
    }

    // Compute degeneracy ordering. This is a crucial heuristic.
    // An O(N^2) implementation is simple and sufficient here.
    std::vector<int> p(N);
    std::vector<int> temp_deg(N + 1);
    for(int i = 1; i <= N; ++i) {
        temp_deg[i] = adj_list[i].size();
    }
    std::vector<bool> removed(N + 1, false);

    for (int i = 0; i < N; ++i) {
        int min_deg_v = -1;
        int min_deg = N + 1;
        // Find the vertex with the minimum degree among non-removed vertices.
        for (int v = 1; v <= N; ++v) {
            if (!removed[v] && temp_deg[v] < min_deg) {
                min_deg = temp_deg[v];
                min_deg_v = v;
            }
        }
        
        p[i] = min_deg_v;
        removed[min_deg_v] = true;

        // Update degrees of its neighbors.
        for (int neighbor : adj_list[min_deg_v]) {
            if (!removed[neighbor]) {
                temp_deg[neighbor]--;
            }
        }
    }
    // The degeneracy order is the reverse of the removal order.
    std::reverse(p.begin(), p.end());

    // This is the main heuristic search for a large clique.
    // It iterates through vertices in degeneracy order and tries to build a clique.
    std::bitset<MAXN> best_clique;
    int max_k = 0;

    // Iterate through vertices from last to first in the degeneracy order.
    for (int i = N - 1; i >= 0; --i) {
        int v = p[i];
        
        // A simple pruning: if the number of remaining vertices is not enough
        // to form a larger clique, we can stop.
        if (i + 1 <= max_k) {
            break;
        }

        std::bitset<MAXN> current_clique;
        current_clique.set(v);

        // Consider candidates for extending the clique.
        // Candidates are neighbors of v that appear after v in the degeneracy order.
        // This avoids redundant computations and trying the same cliques multiple times.
        for (int j = i + 1; j < N; ++j) {
            int u = p[j];
            // The candidate u must be a neighbor of the seed vertex v.
            if (!adj_mat[v][u]) continue;

            // Check if u is connected to all vertices already in current_clique.
            // (adj_mat[u] & current_clique) == current_clique checks if
            // current_clique is a subset of u's neighbors.
            if ((adj_mat[u] & current_clique) == current_clique) {
                current_clique.set(u);
            }
        }
        
        // If we found a larger clique, update our best result.
        if ((int)current_clique.count() > max_k) {
            max_k = current_clique.count();
            best_clique = current_clique;
        }
    }

    // Output the resulting clique in the required format.
    for (int i = 1; i <= N; ++i) {
        if (best_clique[i]) {
            std::cout << 1 << "\n";
        } else {
            std::cout << 0 << "\n";
        }
    }
}

int main() {
    solve();
    return 0;
}