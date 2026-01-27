#include <iostream>
#include <vector>
#include <bitset>
#include <algorithm>
#include <cstdio>
#include <ctime>

using namespace std;

// Maximum number of vertices as per constraints
const int MAXN = 1005;

int N, M;
// Adjacency matrix using bitsets for efficient intersection and checking
bitset<MAXN> adj[MAXN];

// Stores the vertices in the current clique being explored
vector<int> current_clique;
// Stores the vertices of the best clique found so far
vector<int> best_clique;
// Size of the best clique found so far
int best_k = 0;

// Variables for time management
clock_t start_time;
const double TIME_LIMIT = 1.95; // Slightly less than 2.0s to be safe

// Static arrays for the greedy coloring heuristic to avoid repeated allocation
static int used_colors[MAXN];
static int color_cookie = 0;

/**
 * Recursive function to find maximum clique.
 * P: bitset representing the set of candidate vertices for the current step.
 */
void solve(bitset<MAXN> P) {
    // Check time limit to ensure we output something within 2s
    if ((double)(clock() - start_time) / CLOCKS_PER_SEC > TIME_LIMIT) return;

    int p_size = P.count();
    
    // If no candidates left, check if the current clique is the best found so far
    if (p_size == 0) {
        if ((int)current_clique.size() > best_k) {
            best_k = current_clique.size();
            best_clique = current_clique;
        }
        return;
    }

    // Pruning 1: Even if we take all vertices in P, can we beat best_k?
    if ((int)current_clique.size() + p_size <= best_k) return;

    // Convert bitset P to a vector of vertex indices for coloring and iteration
    vector<int> nodes;
    nodes.reserve(p_size);
    for (int i = 1; i <= N; ++i) {
        if (P[i]) nodes.push_back(i);
    }

    // Heuristic: Greedy Graph Coloring on the subgraph induced by P
    // The number of colors used is an upper bound on the maximum clique size in P.
    vector<int> color(N + 1, 0);
    int max_c = 0;

    for (int u : nodes) {
        color_cookie++;
        // Check colors of neighbors in P that are already colored
        for (int v : nodes) {
            if (v == u) continue;
            // adj[u][v] is true if u and v are connected
            if (color[v] != 0 && adj[u][v]) {
                used_colors[color[v]] = color_cookie;
            }
        }
        
        // Find the smallest valid color for u
        int k = 1;
        while (used_colors[k] == color_cookie) k++;
        color[u] = k;
        if (k > max_c) max_c = k;
    }

    // Pruning 2: Coloring Bound
    // Max clique in P cannot exceed the chromatic number of induced subgraph (approx by max_c)
    if ((int)current_clique.size() + max_c <= best_k) return;

    // Sort nodes by color in ascending order.
    // This allows us to process vertices with higher color classes first (by iterating backwards),
    // which enables efficient pruning.
    sort(nodes.begin(), nodes.end(), [&](int a, int b) {
        return color[a] < color[b];
    });

    // Iterate backwards through the sorted nodes
    for (int i = (int)nodes.size() - 1; i >= 0; --i) {
        // Periodic time check
        if ((double)(clock() - start_time) / CLOCKS_PER_SEC > TIME_LIMIT) return;

        int u = nodes[i];
        int c = color[u];

        // Pruning 3: Bound check with specific node color
        // If current clique size + color of u <= best_k, we can prune because
        // all remaining nodes (indices 0 to i-1) have colors <= c, so they can't form
        // a clique large enough to beat best_k.
        if ((int)current_clique.size() + c <= best_k) break;

        // Add u to current clique
        current_clique.push_back(u);
        
        // Remove u from P. 
        // This ensures u is not considered in the candidate sets of sibling recursive calls (nodes[0...i-1]).
        P[u] = 0;
        
        // Recurse
        // New candidates are vertices in P that are neighbors of u.
        solve(P & adj[u]);

        // Backtrack
        current_clique.pop_back();
    }
}

int main() {
    // Read input
    if (scanf("%d %d", &N, &M) != 2) return 0;

    for (int i = 0; i < M; ++i) {
        int u, v;
        scanf("%d %d", &u, &v);
        if (u >= 1 && u <= N && v >= 1 && v <= N) {
            adj[u][v] = 1;
            adj[v][u] = 1;
        }
    }

    start_time = clock();

    // Initial candidates: all vertices 1 to N
    bitset<MAXN> P;
    for (int i = 1; i <= N; ++i) P.set(i);

    solve(P);

    // Output results
    vector<int> result(N + 1, 0);
    for (int v : best_clique) {
        result[v] = 1;
    }

    for (int i = 1; i <= N; ++i) {
        printf("%d\n", result[i]);
    }

    return 0;
}