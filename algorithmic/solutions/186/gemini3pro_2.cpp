#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <cstring>

using namespace std;

const int MAXN = 505;
int N, M;
vector<int> adj[MAXN];
bool adj_mat[MAXN][MAXN]; 
int color[MAXN];
int best_color[MAXN];
int best_k = MAXN + 1;

// DSatur arrays
int deg[MAXN];
int sat_deg[MAXN];
bool colored[MAXN];
bool adj_colors[MAXN][MAXN]; 

// Tabu arrays
int adj_color_count[MAXN][MAXN]; 
int tabu[MAXN][MAXN]; 
int num_conflicts[MAXN]; 
mt19937 rng(1337);

void run_dsatur() {
    memset(colored, 0, sizeof(colored));
    memset(sat_deg, 0, sizeof(sat_deg));
    memset(adj_colors, 0, sizeof(adj_colors));
    
    for(int i=1; i<=N; ++i) deg[i] = adj[i].size();
    
    int processed = 0;
    int max_c = 0;
    
    while(processed < N) {
        int u = -1;
        int max_sat = -1;
        int max_deg = -1;
        
        for(int i=1; i<=N; ++i) {
            if(!colored[i]) {
                if(sat_deg[i] > max_sat) {
                    max_sat = sat_deg[i];
                    max_deg = deg[i];
                    u = i;
                } else if(sat_deg[i] == max_sat) {
                    if(deg[i] > max_deg) {
                        max_deg = deg[i];
                        u = i;
                    }
                }
            }
        }
        
        int c = 1;
        while(true) {
            bool ok = true;
            for(int v : adj[u]) {
                if(colored[v] && color[v] == c) {
                    ok = false;
                    break;
                }
            }
            if(ok) break;
            c++;
        }
        
        color[u] = c;
        colored[u] = true;
        if(c > max_c) max_c = c;
        processed++;
        
        for(int v : adj[u]) {
            if(!colored[v]) {
                if(!adj_colors[v][c]) {
                    adj_colors[v][c] = true;
                    sat_deg[v]++;
                }
            }
        }
    }
    
    if(max_c < best_k) {
        best_k = max_c;
        for(int i=1; i<=N; ++i) best_color[i] = color[i];
    }
}

void init_tabu(int k) {
    for(int i=1; i<=N; ++i) {
        color[i] = (rng() % k) + 1;
    }
    memset(adj_color_count, 0, sizeof(adj_color_count));
    memset(num_conflicts, 0, sizeof(num_conflicts));
    
    for(int u=1; u<=N; ++u) {
        for(int v : adj[u]) {
            adj_color_count[u][color[v]]++;
        }
    }
    
    for(int u=1; u<=N; ++u) {
        num_conflicts[u] = adj_color_count[u][color[u]];
    }
    
    memset(tabu, 0, sizeof(tabu));
}

bool solve_tabu(int k, int max_iters, const chrono::time_point<chrono::high_resolution_clock>& start_time, double time_limit) {
    init_tabu(k);
    
    int total_conflicts = 0;
    for(int u=1; u<=N; ++u) total_conflicts += num_conflicts[u];
    total_conflicts /= 2;
    
    if (total_conflicts == 0) {
        best_k = k;
        for(int i=1; i<=N; ++i) best_color[i] = color[i];
        return true;
    }
    
    int iter = 0;
    
    while(iter < max_iters) {
        if ((iter & 255) == 0) {
            auto now = chrono::high_resolution_clock::now();
            chrono::duration<double> elapsed = now - start_time;
            if (elapsed.count() > time_limit) return false;
        }

        int best_delta = 1e9;
        int best_u = -1;
        int best_c = -1;
        
        vector<int> nodes_in_conflict;
        nodes_in_conflict.reserve(N);
        for(int i=1; i<=N; ++i) {
            if(num_conflicts[i] > 0) nodes_in_conflict.push_back(i);
        }
        
        if(nodes_in_conflict.empty()) {
            best_k = k;
            for(int i=1; i<=N; ++i) best_color[i] = color[i];
            return true;
        }
        
        for(int u : nodes_in_conflict) {
            int old_c = color[u];
            int current_u_conflicts = adj_color_count[u][old_c];
            
            for(int c = 1; c <= k; ++c) {
                if(c == old_c) continue;
                
                int delta = adj_color_count[u][c] - current_u_conflicts;
                
                // Aspiration criteria: found a solution
                if (total_conflicts + delta == 0) {
                    best_u = u;
                    best_c = c;
                    goto apply_move;
                }
                
                bool is_tabu = (tabu[u][c] > iter);
                
                if (!is_tabu) {
                    if (delta < best_delta) {
                        best_delta = delta;
                        best_u = u;
                        best_c = c;
                    } else if (delta == best_delta) {
                        if ((rng() & 1) == 0) {
                            best_u = u;
                            best_c = c;
                        }
                    }
                }
            }
        }
        
        if (best_u == -1) {
            // All improving/non-worsening moves are tabu.
            // Pick the best tabu move (aspiration-like behavior to escape)
             for(int u : nodes_in_conflict) {
                int old_c = color[u];
                int current_u_conflicts = adj_color_count[u][old_c];
                for(int c = 1; c <= k; ++c) {
                    if(c == old_c) continue;
                    int delta = adj_color_count[u][c] - current_u_conflicts;
                    if (delta < best_delta) {
                        best_delta = delta;
                        best_u = u;
                        best_c = c;
                    }
                }
            }
        }
        
        apply_move:
        if (best_u == -1) {
            // Should not happen if conflicts exist and k > 1
            iter++;
            continue;
        }
        
        int u = best_u;
        int old_c = color[u];
        int new_c = best_c;
        
        color[u] = new_c;
        total_conflicts += (adj_color_count[u][new_c] - adj_color_count[u][old_c]);
        
        for(int v : adj[u]) {
            adj_color_count[v][old_c]--;
            adj_color_count[v][new_c]++;
            if (color[v] == old_c) num_conflicts[v]--;
            if (color[v] == new_c) num_conflicts[v]++;
        }
        
        num_conflicts[u] = adj_color_count[u][new_c];
        
        // Tabu tenure: random variation helps robustness
        int tenure = 7 + (rng() % 10);
        tabu[u][old_c] = iter + tenure;
        
        if (total_conflicts == 0) {
            best_k = k;
            for(int i=1; i<=N; ++i) best_color[i] = color[i];
            return true;
        }
        
        iter++;
    }
    
    return false;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N >> M)) return 0;
    
    for(int i=0; i<M; ++i) {
        int u, v;
        cin >> u >> v;
        if(u == v) continue;
        if (adj_mat[u][v]) continue;
        adj_mat[u][v] = adj_mat[v][u] = true;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    auto start_time = chrono::high_resolution_clock::now();
    
    // 1. Initial constructive solution
    run_dsatur();
    
    // 2. Optimization using Tabu Search
    int k = best_k - 1;
    double time_limit = 1.96; 
    
    while(k >= 1) { // M>=1 means k>=2 effectively, but check k>=1 safely
        auto now = chrono::high_resolution_clock::now();
        chrono::duration<double> elapsed = now - start_time;
        if(elapsed.count() > time_limit) break;
        
        bool found = false;
        // Try multiple restarts if time permits
        for(int retry = 0; retry < 10; ++retry) {
            now = chrono::high_resolution_clock::now();
            elapsed = now - start_time;
            if(elapsed.count() > time_limit) break;
            
            // For smaller k, allow more iterations? Or fixed large number.
            // Rely on time limit to break.
            if(solve_tabu(k, 1000000, start_time, time_limit)) {
                found = true;
                break;
            }
        }
        
        if(found) {
            k--;
        } else {
            // Cannot find k coloring, so best_k is k+1
            break; 
        }
    }
    
    for(int i=1; i<=N; ++i) {
        cout << best_color[i] << "\n";
    }
    
    return 0;
}