#include <iostream>
#include <vector>
#include <algorithm>
#include <ctime>
#include <random>

using namespace std;

// Maximum number of vertices as per constraints
const int MAXN = 505;
int N, M;
vector<int> adj[MAXN];
int sol[MAXN];
int best_sol[MAXN];
int best_k = MAXN;

// Gamma: gamma[u][c] = num neighbors of u having color c
int gamma_c[MAXN][MAXN]; 
int tabu[MAXN][MAXN]; // Stores iteration number until which a move is tabu
long long current_conflicts = 0;

// Greedy heuristic to get initial solution
void run_dsatur() {
    vector<int> color(N + 1, -1);
    vector<int> dsat(N + 1, 0);
    vector<int> deg(N + 1, 0);
    vector<bool> colored(N + 1, false);

    for (int i = 1; i <= N; ++i) {
        deg[i] = adj[i].size();
        dsat[i] = deg[i];
    }

    for (int cnt = 0; cnt < N; ++cnt) {
        int u = -1, max_dsat = -1, max_deg = -1;
        for (int i = 1; i <= N; ++i) {
            if (!colored[i]) {
                if (dsat[i] > max_dsat) {
                    max_dsat = dsat[i];
                    max_deg = deg[i];
                    u = i;
                } else if (dsat[i] == max_dsat) {
                    if (deg[i] > max_deg) {
                        max_deg = deg[i];
                        u = i;
                    }
                }
            }
        }

        // Assign smallest available color
        int c = 0;
        while (true) {
            bool conflict = false;
            for (int v : adj[u]) {
                if (colored[v] && color[v] == c) {
                    conflict = true;
                    break;
                }
            }
            if (!conflict) break;
            c++;
        }
        color[u] = c;
        colored[u] = true;

        for (int v : adj[u]) {
            if (!colored[v]) {
                bool c_seen = false;
                for (int w : adj[v]) {
                    if (colored[w] && color[w] == c && w != u) {
                        c_seen = true;
                        break;
                    }
                }
                if (!c_seen) dsat[v]++;
            }
        }
    }
    
    int max_c = 0;
    for (int i = 1; i <= N; ++i) {
        best_sol[i] = color[i];
        max_c = max(max_c, color[i]);
    }
    best_k = max_c + 1;
}

// Build gamma table and calculate total conflicts for current solution 'sol'
void build_gamma(int k) {
    for (int i = 1; i <= N; ++i) {
        for (int c = 0; c < k; ++c) gamma_c[i][c] = 0;
    }
    current_conflicts = 0;
    
    for (int u = 1; u <= N; ++u) {
        for (int v : adj[u]) {
            gamma_c[u][sol[v]]++;
        }
    }
    
    for (int u = 1; u <= N; ++u) {
        current_conflicts += gamma_c[u][sol[u]];
    }
    current_conflicts /= 2;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        if (u != v) {
             adj[u].push_back(v);
             adj[v].push_back(u);
        }
    }

    // Get an initial valid coloring
    run_dsatur();
    
    int target_k = best_k - 1;
    mt19937 rng(1337);
    clock_t start_time = clock();
    vector<int> candidates;
    vector<int> C_nodes;
    candidates.reserve(MAXN);
    C_nodes.reserve(MAXN);

    // Iterative optimization loop: try to color with fewer colors using Tabu Search
    while (true) {
        // Time limit check (approx 2s total limit, safe margin 1.95s)
        if ((double)(clock() - start_time) / CLOCKS_PER_SEC > 1.95) break;

        // Initialize random solution with target_k colors
        for (int i = 1; i <= N; ++i) sol[i] = rng() % target_k;
        
        build_gamma(target_k);
        for(int i=0; i<=N; ++i) 
            for(int c=0; c<target_k; ++c) tabu[i][c] = 0;

        int iter = 0;
        long long min_conflicts = current_conflicts;

        while (current_conflicts > 0) {
            iter++;
            if ((iter & 1023) == 0) {
                 if ((double)(clock() - start_time) / CLOCKS_PER_SEC > 1.95) break;
            }
            // Restart random initialization if stuck
            if (iter > 200000) break; 

            // Identify conflicting nodes
            C_nodes.clear();
            for (int i = 1; i <= N; ++i) {
                if (gamma_c[i][sol[i]] > 0) C_nodes.push_back(i);
            }
            if (C_nodes.empty()) break; // Valid solution found

            // Pick a random conflicting vertex
            int u = C_nodes[rng() % C_nodes.size()];
            int cur_c = sol[u];
            
            // Find best move
            int best_delta = 1e9;
            candidates.clear();
            
            // Evaluate all possible colors
            for (int c = 0; c < target_k; ++c) {
                if (c == cur_c) continue;
                int delta = gamma_c[u][c] - gamma_c[u][cur_c];
                
                // Tabu and Aspiration check
                // Allowed if not tabu OR (tabu but improves global best conflicts)
                if (tabu[u][c] <= iter || (current_conflicts + delta < min_conflicts)) {
                    if (delta < best_delta) {
                        best_delta = delta;
                        candidates.clear();
                        candidates.push_back(c);
                    } else if (delta == best_delta) {
                        candidates.push_back(c);
                    }
                }
            }

            // If all moves tabu and no aspiration, pick best move anyway
            if (candidates.empty()) {
                best_delta = 1e9;
                for (int c = 0; c < target_k; ++c) {
                    if (c == cur_c) continue;
                    int delta = gamma_c[u][c] - gamma_c[u][cur_c];
                    if (delta < best_delta) {
                        best_delta = delta;
                        candidates.clear();
                        candidates.push_back(c);
                    } else if (delta == best_delta) {
                        candidates.push_back(c);
                    }
                }
            }
            
            if (candidates.empty()) continue; 

            int next_c = candidates[rng() % candidates.size()];
            int delta = best_delta;

            // Apply move
            sol[u] = next_c;
            current_conflicts += delta;
            
            if (current_conflicts < min_conflicts) min_conflicts = current_conflicts;

            // Update neighbor counts
            for (int v : adj[u]) {
                gamma_c[v][cur_c]--;
                gamma_c[v][next_c]++;
            }

            // Set tabu tenure
            int tenure = 7 + (rng() % 10);
            tabu[u][cur_c] = iter + tenure; // Forbid moving back to old color
        }

        if (current_conflicts == 0) {
            // Found a valid coloring with target_k
            for (int i = 1; i <= N; ++i) best_sol[i] = sol[i];
            best_k = target_k;
            target_k--;
            if (target_k < 1) break;
        }
    }

    for (int i = 1; i <= N; ++i) cout << best_sol[i] + 1 << "\n";
    return 0;
}