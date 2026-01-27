/**
 * Solution for Clique Cover Challenge
 * Map problem to Graph Coloring on the Complement Graph G'.
 * A clique partition in G is equivalent to a proper vertex coloring in G'.
 * 
 * Approach:
 * 1. Construct complement graph G'.
 * 2. Generate initial solution using a Greedy heuristic (randomized DSatur-like).
 * 3. Use Tabu Search (Tabucol) to iteratively reduce the number of colors K.
 */

#include <iostream>
#include <vector>
#include <bitset>
#include <algorithm>
#include <random>
#include <ctime>
#include <cstring>
#include <numeric>

using namespace std;

// Maximum number of vertices as per constraints
const int MAXN = 505;

// Global Data Structures
int N;
bitset<MAXN> adj_comp[MAXN]; // Adjacency matrix of complement graph G'
vector<int> adj_list[MAXN];  // Adjacency list of G'
int color[MAXN];             // Current working coloring
int best_color[MAXN];        // Best valid coloring found so far
int best_k = MAXN + 1;       // Minimize this (number of cliques)

// Tabu Search Structures
// adj_color_count[u][c]: number of neighbors of u (in G') that currently have color c
int adj_color_count[MAXN][MAXN];
// tabu_tenure[u][c]: iteration number until which moving vertex u to color c is forbidden
int tabu_tenure[MAXN][MAXN];
// conflicts[u]: number of neighbors of u in G' that share the same color as u
int conflicts[MAXN];

// Utility
mt19937 rng(1337);
clock_t start_time;
const double TIME_LIMIT = 1.95;

inline double get_time() {
    return (double)(clock() - start_time) / CLOCKS_PER_SEC;
}

// Greedy coloring heuristic
// Assigns the smallest legal color to vertices based on the order in permutation p
// Returns the number of colors used
int greedy_coloring(const vector<int>& p, int* output_sol) {
    int max_c = 0;
    // Clearing output array/vector implies uncolored
    for (int u : p) output_sol[u] = 0;

    for (int u : p) {
        // Check neighbors to find generic forbidden colors
        // Since K <= N, a direct check is O(degree)
        // For speed with N=500, we can use a boolean array reset per node or check on fly
        // We'll iterate colors starting from 1
        int c = 1;
        while (true) {
            bool conflict = false;
            for (int v : adj_list[u]) {
                if (output_sol[v] == c) {
                    conflict = true;
                    break;
                }
            }
            if (!conflict) break;
            c++;
        }
        output_sol[u] = c;
        if (c > max_c) max_c = c;
    }
    return max_c;
}

// Tabu Search optimization to find a valid coloring with k colors
// Tries to eliminate all conflicts for a given k
void solve_tabu(int k) {
    // Initialize random coloring with k colors
    uniform_int_distribution<int> dist(1, k);
    
    // Reset structures
    for (int i = 1; i <= N; ++i) {
        color[i] = dist(rng);
        conflicts[i] = 0;
        for (int c = 1; c <= k; ++c) {
            adj_color_count[i][c] = 0;
            tabu_tenure[i][c] = 0;
        }
    }
    
    // Initial computation of conflicts and neighbor color counts
    int total_conflicts = 0;
    for (int u = 1; u <= N; ++u) {
        for (int v : adj_list[u]) {
            adj_color_count[u][color[v]]++;
        }
    }
    for (int u = 1; u <= N; ++u) {
        conflicts[u] = adj_color_count[u][color[u]];
        total_conflicts += conflicts[u];
    }
    total_conflicts /= 2; // Edges counted twice

    if (total_conflicts == 0) {
        memcpy(best_color, color, sizeof(color));
        best_k = k;
        return;
    }

    int iter = 0;
    const int max_iter_limit = 200000; // Restart if stuck too long
    
    // Dynamic sampling parameters to keep iteration fast
    int sample_size = 20;
    if (k > 50) sample_size = 10;
    if (k > 200) sample_size = 5;
    
    vector<int> conf_nodes;
    conf_nodes.reserve(N);

    while (iter < max_iter_limit) {
        if ((iter & 1023) == 0 && get_time() > TIME_LIMIT) return;
        iter++;

        // Identify vertices involved in conflicts
        conf_nodes.clear();
        for (int i = 1; i <= N; ++i) {
            if (conflicts[i] > 0) conf_nodes.push_back(i);
        }

        if (conf_nodes.empty()) {
            // Solution found
            memcpy(best_color, color, sizeof(color));
            best_k = k;
            return;
        }

        // Select a move
        int best_u = -1;
        int best_c = -1;
        int best_delta = 1e9;
        
        // We only check a subset of conflicting nodes to speed up the loop
        int check_count = (int)conf_nodes.size();
        if (check_count > sample_size) check_count = sample_size;

        for (int t = 0; t < check_count; ++t) {
            // Pick random conflicting node
            int idx = rng() % conf_nodes.size();
            int u = conf_nodes[idx];
            int curr_c = color[u];

            // Try changing color of u
            for (int c = 1; c <= k; ++c) {
                if (c == curr_c) continue;
                
                // Calculate change in total conflicts if u moves to c
                // Delta = (conflicts in new color) - (conflicts in old color)
                int delta = adj_color_count[u][c] - adj_color_count[u][curr_c];
                
                // Tabu check & Aspiration
                // Aspiration: if move leads to 0 conflicts, take it regardless of tabu
                bool is_tabu = (tabu_tenure[u][c] > iter);
                if (total_conflicts + delta == 0) is_tabu = false; 

                if (!is_tabu) {
                    if (delta < best_delta) {
                        best_delta = delta;
                        best_u = u;
                        best_c = c;
                    } else if (delta == best_delta) {
                        // Tie-break randomly to encourage exploration
                        if (rng() & 1) {
                            best_u = u;
                            best_c = c;
                        }
                    }
                }
            }
        }

        // If no valid non-tabu move found, force a random move to escape
        if (best_u == -1) {
             int idx = rng() % conf_nodes.size();
             best_u = conf_nodes[idx];
             do {
                 best_c = (rng() % k) + 1;
             } while (best_c == color[best_u]);
             best_delta = adj_color_count[best_u][best_c] - adj_color_count[best_u][color[best_u]];
        }

        // Apply best move
        int u = best_u;
        int old_c = color[u];
        int new_c = best_c;
        
        color[u] = new_c;
        total_conflicts += best_delta;

        // Update data structures
        for (int v : adj_list[u]) {
            adj_color_count[v][old_c]--;
            adj_color_count[v][new_c]++;
            if (color[v] == old_c) conflicts[v]--;
            if (color[v] == new_c) conflicts[v]++;
        }
        conflicts[u] = adj_color_count[u][new_c];

        // Update Tabu tenure
        // Dynamic tenure helps stability
        int tenure = 10 + (rng() % 10) + (int)(0.6 * total_conflicts);
        tabu_tenure[u][old_c] = iter + tenure;

        if (total_conflicts == 0) {
            memcpy(best_color, color, sizeof(color));
            best_k = k;
            return;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    start_time = clock();

    int M;
    if (!(cin >> N >> M)) return 0;

    // Initialize G' as a complete graph
    for (int i = 1; i <= N; ++i) {
        adj_comp[i].set();     // Set all bits to 1
        adj_comp[i].reset(i);  // No self loops
        adj_comp[i].reset(0);  // Ignore index 0
    }

    // Read edges of G. Edge (u, v) in G means NO edge in G'.
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj_comp[u].reset(v);
        adj_comp[v].reset(u);
    }

    // Convert bitsets to adjacency lists for faster iteration
    for (int i = 1; i <= N; ++i) {
        for (int j = 1; j <= N; ++j) {
            if (adj_comp[i].test(j)) {
                adj_list[i].push_back(j);
            }
        }
    }

    // PHASE 1: Greedy Construction
    // Attempt multiple greedy colorings with random vertex orderings
    vector<int> p(N);
    iota(p.begin(), p.end(), 1);
    
    int temp_sol[MAXN];
    int num_initial_tries = 30;

    // First try sorted by degree (Largest Degree First) which is often good
    sort(p.begin(), p.end(), [&](int a, int b){
        return adj_list[a].size() > adj_list[b].size();
    });
    int start_k = greedy_coloring(p, temp_sol);
    best_k = start_k;
    memcpy(best_color, temp_sol, sizeof(temp_sol));

    // Random shuffles
    for (int i = 0; i < num_initial_tries && get_time() < TIME_LIMIT; ++i) {
        shuffle(p.begin(), p.end(), rng);
        int k = greedy_coloring(p, temp_sol);
        if (k < best_k) {
            best_k = k;
            memcpy(best_color, temp_sol, sizeof(temp_sol));
        }
    }

    // PHASE 2: Tabu Search Optimization
    // Iteratively try to find a valid coloring with best_k - 1 colors
    while (best_k > 1 && get_time() < TIME_LIMIT) {
        int target_k = best_k - 1;
        int prev_k = best_k;
        
        solve_tabu(target_k);
        
        // If solve_tabu found a solution, it updated best_k to target_k.
        // If it failed (timeout or max iter), best_k remains same.
        // We loop again; if best_k didn't change, we retry the same target (random restart).
    }

    // Output Result
    // id[i] corresponds to best_color[i]
    for (int i = 1; i <= N; ++i) {
        cout << best_color[i] << "\n";
    }

    return 0;
}