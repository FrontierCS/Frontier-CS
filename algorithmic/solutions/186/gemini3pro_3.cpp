#include <iostream>
#include <vector>
#include <algorithm>
#include <ctime>
#include <cstdlib>
#include <cstring>
#include <random>

using namespace std;

// Constants
const int MAXN = 505;
const double TIME_LIMIT = 1.95;

// Graph and State
int N, M;
vector<int> adj_list[MAXN];
int colors[MAXN];       // Current working coloring
int best_colors[MAXN];  // Best valid coloring found
int current_k;          // Number of colors in best_colors

// Tabu Search Data Structures
int gamma_c[MAXN][MAXN]; // gamma_c[u][c] = number of neighbors of u currently colored c
int tabu[MAXN][MAXN];    // tabu[u][c] = iteration until which moving u to c is tabu
bool in_conflict[MAXN];  // Track if a vertex is currently involved in a conflict
vector<int> conflicting_nodes; // List of vertices in conflict

// Utilities
clock_t start_time;
mt19937 rng(1337);

// Greedy DSatur Algorithm for initial solution
void dsatur() {
    vector<int> c(N + 1, 0);
    vector<int> sat(N + 1, 0);
    vector<int> deg(N + 1, 0);
    vector<bool> colored(N + 1, false);

    for (int i = 1; i <= N; ++i) deg[i] = adj_list[i].size();

    int colored_cnt = 0;
    while (colored_cnt < N) {
        int u = -1, max_sat = -1, max_deg = -1;
        // Select vertex with max saturation, break ties with max degree
        for (int v = 1; v <= N; ++v) {
            if (!colored[v]) {
                if (sat[v] > max_sat) {
                    max_sat = sat[v];
                    max_deg = deg[v];
                    u = v;
                } else if (sat[v] == max_sat) {
                    if (deg[v] > max_deg) {
                        max_deg = deg[v];
                        u = v;
                    }
                }
            }
        }

        // Assign smallest valid color
        vector<bool> used(N + 1, false);
        for (int v : adj_list[u]) {
            if (colored[v]) {
                if(c[v] <= N) used[c[v]] = true;
            }
        }
        int color = 1;
        while (color <= N && used[color]) color++;
        c[u] = color;
        colored[u] = true;
        colored_cnt++;

        // Update saturation degrees of neighbors
        for (int v : adj_list[u]) {
            if (!colored[v]) {
                bool already_adj = false;
                for (int w : adj_list[v]) {
                    if (colored[w] && c[w] == color && w != u) {
                        already_adj = true;
                        break;
                    }
                }
                if (!already_adj) sat[v]++;
            }
        }
    }

    int max_c = 0;
    for (int i = 1; i <= N; ++i) {
        best_colors[i] = c[i];
        max_c = max(max_c, c[i]);
    }
    current_k = max_c;
}

// Build internal structures (gamma table, conflict list) for a new k
int build_structures(int k) {
    int total_conflicts = 0;
    conflicting_nodes.clear();
    for (int u = 1; u <= N; ++u) {
        for (int c = 1; c <= k; ++c) gamma_c[u][c] = 0;
        in_conflict[u] = false;
    }

    // Fill gamma table: count neighbor colors
    for (int u = 1; u <= N; ++u) {
        for (int v : adj_list[u]) {
            gamma_c[u][colors[v]]++;
        }
    }

    // Identify conflicts
    for (int u = 1; u <= N; ++u) {
        if (gamma_c[u][colors[u]] > 0) {
            in_conflict[u] = true;
            conflicting_nodes.push_back(u);
            total_conflicts += gamma_c[u][colors[u]];
        }
    }
    return total_conflicts / 2; // Each edge counted twice
}

// Try to find a valid coloring with k colors using Tabu Search (TabuCol)
bool solve_k(int k) {
    // Random initialization
    uniform_int_distribution<int> dist(1, k);
    for (int i = 1; i <= N; ++i) colors[i] = dist(rng);

    // Reset tabu tenure
    memset(tabu, 0, sizeof(tabu));
    
    int conflicts = build_structures(k);
    if (conflicts == 0) return true;

    long long iter = 0;
    
    while (true) {
        iter++;
        // Check time limit periodically
        if ((iter & 0xFFF) == 0) { 
            if ((double)(clock() - start_time) / CLOCKS_PER_SEC > TIME_LIMIT) return false;
        }

        // Rebuild conflict list if empty but conflicts exist (sanity check)
        if (conflicting_nodes.empty() && conflicts > 0) {
             conflicts = build_structures(k);
        }
        if (conflicts == 0) return true;

        int best_u = -1;
        int best_c = -1;
        int best_delta = 1e9;
        
        // Strategy: Scan conflicting nodes to find the best move (steepest descent)
        // If too many checks, we could sample, but for N=500 full scan is acceptable often.
        // We limit work if needed.
        
        int n_conf = conflicting_nodes.size();
        
        int best_tabu_delta = 1e9;
        int best_tabu_u = -1;
        int best_tabu_c = -1;

        // Iterate over conflicting nodes
        for (int idx = 0; idx < n_conf; ++idx) {
            int u = conflicting_nodes[idx];
            int current_c = colors[u];
            int current_pen = gamma_c[u][current_c];

            // Evaluate moving u to color c
            for (int c = 1; c <= k; ++c) {
                if (c == current_c) continue;
                
                // Delta = (conflicts if moved) - (current conflicts for u)
                // gamma_c[u][c] is the number of neighbors with color c.
                // Moving u to c adds gamma_c[u][c] conflicts and removes gamma_c[u][current_c] conflicts.
                int delta = gamma_c[u][c] - current_pen;
                
                if (tabu[u][c] <= iter) {
                    // Non-tabu move
                    if (delta < best_delta) {
                        best_delta = delta;
                        best_u = u;
                        best_c = c;
                    } else if (delta == best_delta) {
                        // Random tie-break
                        if (rng() % 2) {
                            best_u = u;
                            best_c = c;
                        }
                    }
                } else {
                    // Tabu move - Aspiration criterion
                    if (conflicts + delta == 0) { // If it solves the problem, take it
                        best_delta = delta;
                        best_u = u;
                        best_c = c;
                        goto APPLY_MOVE;
                    }
                    // Track best tabu move just in case
                    if (delta < best_tabu_delta) {
                        best_tabu_delta = delta;
                        best_tabu_u = u;
                        best_tabu_c = c;
                    }
                }
            }
        }

        // If no non-tabu move found (or all are worse than best tabu?)
        if (best_u == -1) {
            if (best_tabu_u != -1) {
                best_u = best_tabu_u;
                best_c = best_tabu_c;
                best_delta = best_tabu_delta;
            } else {
                // Fallback: random move on random conflicting node
                if (n_conf > 0) {
                    best_u = conflicting_nodes[rng() % n_conf];
                    do {
                        best_c = (rng() % k) + 1;
                    } while (best_c == colors[best_u]);
                    best_delta = gamma_c[best_u][best_c] - gamma_c[best_u][colors[best_u]];
                } else return true;
            }
        }

        APPLY_MOVE:;

        int u = best_u;
        int old_c = colors[u];
        int new_c = best_c;
        
        colors[u] = new_c;
        conflicts += best_delta;
        
        // Set tabu tenure: dependent on problem size and conflict count
        int tenure = (int)(0.6 * conflicts) + (rng() % 10) + 1;
        tabu[u][old_c] = iter + tenure;
        
        // Check u's conflict status after move
        // gamma_c[u][new_c] tells how many neighbors have the new color
        int pen_u = gamma_c[u][new_c];
        if (pen_u == 0 && in_conflict[u]) {
            in_conflict[u] = false;
        } else if (pen_u > 0 && !in_conflict[u]) {
            in_conflict[u] = true;
        }
        
        // Update neighbors' gamma tables and status
        for (int v : adj_list[u]) {
            gamma_c[v][old_c]--;
            gamma_c[v][new_c]++;
            
            int pen_v = gamma_c[v][colors[v]];
            if (pen_v == 0 && in_conflict[v]) {
                in_conflict[v] = false;
            } else if (pen_v > 0 && !in_conflict[v]) {
                in_conflict[v] = true;
            }
        }
        
        // Rebuild conflicting nodes list
        // For N=500 this linear scan is fast enough and simpler than tracking indices
        conflicting_nodes.clear();
        for(int i=1; i<=N; ++i) {
            if (in_conflict[i]) conflicting_nodes.push_back(i);
        }
    }
}

int main() {
    // Optimization for faster I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    start_time = clock();

    if (!(cin >> N >> M)) return 0;
    
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        if (u != v) {
            adj_list[u].push_back(v);
            adj_list[v].push_back(u);
        }
    }
    
    // Remove duplicate edges
    for (int i = 1; i <= N; ++i) {
        sort(adj_list[i].begin(), adj_list[i].end());
        adj_list[i].erase(unique(adj_list[i].begin(), adj_list[i].end()), adj_list[i].end());
    }
    
    // 1. Generate Initial Solution using DSatur
    dsatur();
    
    // 2. Improve solution using Tabu Search
    // Attempt to reduce colors from current_k - 1 downwards
    int k = current_k - 1;
    while (k >= 1) {
        // If successful, solve_k returns true and best_colors should be updated.
        // solve_k works on global 'colors' array.
        if (solve_k(k)) {
            // Found valid k-coloring
            for (int i = 1; i <= N; ++i) best_colors[i] = colors[i];
            current_k = k;
            k--;
        } else {
            // Failed to find solution in time
            break;
        }
        
        // Global time check
        if ((double)(clock() - start_time) / CLOCKS_PER_SEC > TIME_LIMIT) break;
    }
    
    // Output result
    for (int i = 1; i <= N; ++i) {
        cout << best_colors[i] << "\n";
    }

    return 0;
}