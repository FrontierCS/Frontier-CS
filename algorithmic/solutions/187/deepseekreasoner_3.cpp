#include <iostream>
#include <vector>
#include <algorithm>
#include <ctime>
#include <cstdlib>
#include <cstring>
#include <iomanip>

using namespace std;

// Constants and Globals
const int MAXN = 505;
int N, M;

// Adjacency for Complement Graph
vector<int> adj[MAXN]; 
int degree[MAXN];

// Colors
int best_colors[MAXN];
int best_k = 9999;

// Working Solution
int colors[MAXN]; // 0 to k-1
int adj_colors[MAXN][MAXN]; // [u][c] -> count of neighbors of u in G_complement having color c
int tabu[MAXN][MAXN]; // [u][c] -> iteration number when forbidden

// Timing
clock_t start_clock;
const double TIME_LIMIT = 1.95; 

inline double get_elapsed() {
    return (double)(clock() - start_clock) / CLOCKS_PER_SEC;
}

// DSatur Initialization
void solve_dsatur() {
    // Colors 1-based
    vector<int> c(N + 1, 0);
    vector<int> sat_deg(N + 1, 0);
    vector<bool> colored(N + 1, false);
    
    // incremental tracking of colors used by neighbors
    static int neighbor_colors[MAXN][MAXN]; 
    memset(neighbor_colors, 0, sizeof(neighbor_colors));

    for (int i = 0; i < N; ++i) {
        // Pick vertex
        int best_u = -1;
        int max_sat = -1;
        int max_deg = -1;

        for (int u = 1; u <= N; ++u) {
            if (!colored[u]) {
                if (sat_deg[u] > max_sat) {
                    max_sat = sat_deg[u];
                    max_deg = degree[u];
                    best_u = u;
                } else if (sat_deg[u] == max_sat) {
                    if (degree[u] > max_deg) {
                        max_deg = degree[u];
                        best_u = u;
                    }
                }
            }
        }

        if (best_u == -1) break;

        int u = best_u;
        // Assign smallest valid color
        int color = 1;
        while (true) {
            if (neighbor_colors[u][color] == 0) {
                break;
            }
            color++;
        }

        c[u] = color;
        colored[u] = true;

        // Update neighbors
        for (int v : adj[u]) {
            if (!colored[v]) {
                if (neighbor_colors[v][color] == 0) {
                    sat_deg[v]++;
                }
                neighbor_colors[v][color]++;
            }
        }
    }

    // Save
    int max_c = 0;
    for (int i = 1; i <= N; ++i) max_c = max(max_c, c[i]);
    best_k = max_c;
    for (int i = 1; i <= N; ++i) best_colors[i] = c[i];
}

// Tabu Search
bool solve_tabu(int k) {
    // Random init
    for (int i = 1; i <= N; ++i) colors[i] = rand() % k;
    
    memset(adj_colors, 0, sizeof(adj_colors));
    int conflicts = 0;

    for (int u = 1; u <= N; ++u) {
        for (int v : adj[u]) {
            adj_colors[u][colors[v]]++;
            if (u < v && colors[u] == colors[v]) {
                conflicts++;
            }
        }
    }
    
    memset(tabu, 0, sizeof(tabu));
    long long iter = 0;
    int max_iter_limit = 200000; 
    
    while (conflicts > 0 && iter < max_iter_limit) {
        iter++;
        if ((iter & 0xFF) == 0) {
            if (get_elapsed() > TIME_LIMIT) return false;
        }

        int best_u = -1;
        int best_c = -1;
        int best_delta = 1e9;
        
        int conflict_nodes_count = 0;
        
        for (int u = 1; u <= N; ++u) {
            if (adj_colors[u][colors[u]] == 0) continue; 
            conflict_nodes_count++;
            
            int u_c = colors[u];
            int current_conflict_val = adj_colors[u][u_c];
            
            for (int c = 0; c < k; ++c) {
                if (c == u_c) continue;
                
                int delta = adj_colors[u][c] - current_conflict_val;
                
                if (tabu[u][c] >= iter) {
                    if (conflicts + delta > 0) continue;
                }
                
                if (delta < best_delta) {
                    best_delta = delta;
                    best_u = u;
                    best_c = c;
                } else if (delta == best_delta) {
                    if (rand() & 1) { 
                        best_u = u;
                        best_c = c;
                    }
                }
            }
        }
        
        if (best_u == -1) {
             for(int u=1; u<=N; ++u) {
                 if (adj_colors[u][colors[u]] > 0) {
                     best_u = u;
                     best_c = rand() % k;
                     while(best_c == colors[u]) best_c = rand() % k;
                     best_delta = adj_colors[u][best_c] - adj_colors[u][colors[u]];
                     break;
                 }
             }
        }
        
        int u = best_u;
        int old_c = colors[u];
        int new_c = best_c;
        
        colors[u] = new_c;
        conflicts += best_delta;
        
        for (int v : adj[u]) {
            adj_colors[v][old_c]--;
            adj_colors[v][new_c]++;
        }
        
        int tenure = 5 + (rand() % 10) + (int)(conflicts * 0.4);
        tabu[u][old_c] = iter + tenure;
    }
    
    return (conflicts == 0);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    start_clock = clock();
    srand(1337); 
    
    if (!(cin >> N >> M)) return 0;
    
    static bool is_edge[MAXN][MAXN]; 
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        is_edge[u][v] = is_edge[v][u] = true;
    }
    
    // Build Complement Graph
    for (int i = 1; i <= N; ++i) {
        for (int j = i + 1; j <= N; ++j) {
            if (!is_edge[i][j]) {
                adj[i].push_back(j);
                adj[j].push_back(i);
            }
        }
        degree[i] = adj[i].size();
    }
    
    solve_dsatur();
    
    int current_target = best_k - 1;
    
    while (current_target > 0 && get_elapsed() < TIME_LIMIT) {
        bool solved = false;
        int restarts = 0;
        while(get_elapsed() < TIME_LIMIT) {
            if (solve_tabu(current_target)) {
                solved = true;
                break;
            }
            restarts++;
            if (restarts > 5) break; 
        }
        
        if (solved) {
            best_k = current_target;
            for (int i = 1; i <= N; ++i) best_colors[i] = colors[i] + 1; 
            current_target--;
        } else {
            break; 
        }
    }
    
    for (int i = 1; i <= N; ++i) {
        cout << best_colors[i] << "\n";
    }
    
    return 0;
}