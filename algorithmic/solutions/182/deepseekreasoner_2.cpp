#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <ctime>
#include <numeric>

using namespace std;

// Structure to store edge information
struct Edge {
    int u, v;
};

// Global variables
int N, M;
vector<Edge> edges;
vector<vector<int>> adj; // adj[u] contains indices of incident edges
vector<int> best_sol;    // Stores the best valid configuration found
int best_k;              // Size of the best solution found

void solve() {
    // Time limit handling (aiming for slightly under 2.0s)
    double time_limit = 1.9;
    clock_t start_time = clock();

    // Random number generator
    mt19937 rng(1337);

    // Initialize best solution with all vertices (trivial valid solution)
    best_sol.assign(N + 1, 1);
    best_k = N;

    // Precompute static degrees
    vector<int> static_deg(N + 1, 0);
    for (const auto& e : edges) {
        static_deg[e.u]++;
        static_deg[e.v]++;
    }

    // Allocate reusable memory for the loop to improve performance
    vector<int> sol(N + 1);
    vector<int> curr_deg(N + 1);
    vector<int> edge_status(M);         // 0: uncovered, 1: covered
    vector<int> uncovered_edges(M);     // List of indices of uncovered edges
    vector<int> pos_in_uncovered(M);    // Map edge_index -> position in uncovered_edges
    vector<int> cover_count(M);         // Number of selected vertices covering an edge
    vector<int> sol_nodes;              // List of vertices in current solution
    sol_nodes.reserve(N);

    // Repeatedly generate solutions until time limit
    while (true) {
        // Check elapsed time
        double elapsed = (double)(clock() - start_time) / CLOCKS_PER_SEC;
        if (elapsed > time_limit) break;

        // --- Iteration Initialization ---
        fill(sol.begin(), sol.end(), 0);
        
        // Use static degrees as initial dynamic degrees
        curr_deg = static_deg;

        // Reset edge status lists
        for (int i = 0; i < M; ++i) {
            uncovered_edges[i] = i;
            pos_in_uncovered[i] = i;
            edge_status[i] = 0;
        }
        int rem_count = M; // Number of uncovered edges
        int current_k = 0;

        // --- Greedy Construction Phase ---
        // Heuristic: Pick a random uncovered edge and satisfy it by choosing
        // the endpoint with higher dynamic degree.
        while (rem_count > 0) {
            // Pick a random uncovered edge efficiently
            int rand_pos = rng() % rem_count;
            int e_idx = uncovered_edges[rand_pos];
            
            int u = edges[e_idx].u;
            int v = edges[e_idx].v;

            // Choose vertex u or v
            int choice = -1;
            if (curr_deg[u] > curr_deg[v]) choice = u;
            else if (curr_deg[v] > curr_deg[u]) choice = v;
            else {
                // Tie-breaking: Random choice
                choice = (rng() & 1) ? u : v;
            }

            // Add chosen vertex to solution
            sol[choice] = 1;
            current_k++;

            // Update graph state: mark incident edges as covered
            for (int inc_e : adj[choice]) {
                if (edge_status[inc_e] == 1) continue; // Already covered

                edge_status[inc_e] = 1;

                // Remove from uncovered_edges list in O(1)
                int p = pos_in_uncovered[inc_e];
                int last_val = uncovered_edges[rem_count - 1];
                
                uncovered_edges[p] = last_val;
                pos_in_uncovered[last_val] = p;
                
                rem_count--;

                // Decrease effective degree of the neighbor
                int neighbor = (edges[inc_e].u == choice) ? edges[inc_e].v : edges[inc_e].u;
                curr_deg[neighbor]--;
            }
        }

        // --- Pruning Phase ---
        // Try to remove redundant vertices to minimize size.
        // A vertex is redundant if all its incident edges are covered by other vertices in S.
        
        // Calculate coverage counts
        fill(cover_count.begin(), cover_count.end(), 0);
        sol_nodes.clear();
        for (int i = 1; i <= N; ++i) {
            if (sol[i]) {
                sol_nodes.push_back(i);
                for (int e_idx : adj[i]) {
                    cover_count[e_idx]++;
                }
            }
        }

        // Shuffle processing order to explore different local optima
        shuffle(sol_nodes.begin(), sol_nodes.end(), rng);

        for (int u : sol_nodes) {
            // Check redundancy
            bool redundant = true;
            for (int e_idx : adj[u]) {
                // If an edge is covered only by u (count==1), u cannot be removed
                if (cover_count[e_idx] < 2) {
                    redundant = false;
                    break;
                }
            }

            if (redundant) {
                // Remove u from solution
                sol[u] = 0;
                current_k--;
                // Update cover counts
                for (int e_idx : adj[u]) {
                    cover_count[e_idx]--;
                }
            }
        }

        // --- Update Global Best ---
        if (current_k < best_k) {
            best_k = current_k;
            best_sol = sol;
        }
    }
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (cin >> N >> M) {
        adj.resize(N + 1);
        edges.reserve(M);

        for (int i = 0; i < M; ++i) {
            int u, v;
            cin >> u >> v;
            edges.push_back({u, v});
            // Store edge index in adjacency list
            adj[u].push_back(i);
            adj[v].push_back(i);
        }

        solve();

        // Output results in the specified format
        for (int i = 1; i <= N; ++i) {
            cout << best_sol[i] << "\n";
        }
    }
    return 0;
}