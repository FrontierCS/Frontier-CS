#include <iostream>
#include <vector>
#include <algorithm>
#include <set>
#include <random>
#include <ctime>
#include <chrono>
#include <cstring>

using namespace std;

const int MAXN = 505;
int N, M;
vector<int> adj[MAXN];
int adj_mat[MAXN][MAXN]; 

// Solution state
int best_sol_color[MAXN];
int best_k = MAXN + 1;

// Tabu search structures
int current_color[MAXN];
int adj_colors[MAXN][MAXN]; // [u][c] count of neighbors of u with color c
int conflicts[MAXN]; // number of conflicts for node u
long long total_conflicts = 0;
int tabu[MAXN][MAXN]; // tabu[u][c] -> iteration when move (u,c) is allowed
int iter_cnt = 0;

mt19937 rng(1337);

void read_input() {
    if (!(cin >> N >> M)) return;
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue;
        u--; v--; // 0-indexed
        if (adj_mat[u][v]) continue;
        adj_mat[u][v] = adj_mat[v][u] = 1;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
}

// Constructive heuristic: DSatur
void run_dsatur() {
    vector<int> colors(N, -1);
    vector<int> sat_degree(N, 0);
    vector<int> degree(N);
    for(int i=0; i<N; ++i) degree[i] = adj[i].size();

    int colored_cnt = 0;
    
    while(colored_cnt < N) {
        int best_u = -1;
        int max_sat = -1;
        int max_deg = -1;
        
        for(int i=0; i<N; ++i) {
            if(colors[i] == -1) {
                if(sat_degree[i] > max_sat) {
                    max_sat = sat_degree[i];
                    max_deg = degree[i];
                    best_u = i;
                } else if(sat_degree[i] == max_sat) {
                    if(degree[i] > max_deg) {
                        max_deg = degree[i];
                        best_u = i;
                    }
                }
            }
        }
        
        if (best_u == -1) break; 

        vector<bool> used_colors(N, false);
        for(int v : adj[best_u]) {
            if(colors[v] != -1) {
                if(colors[v] < N) used_colors[colors[v]] = true;
            }
        }
        int c = 0;
        while(c < N && used_colors[c]) c++;
        colors[best_u] = c;
        colored_cnt++;
        
        for(int v : adj[best_u]) {
            if(colors[v] == -1) {
                bool seen = false;
                for(int neighbor : adj[v]) {
                    if(colors[neighbor] == c && neighbor != best_u) {
                        seen = true;
                        break;
                    }
                }
                if(!seen) sat_degree[v]++;
            }
        }
    }
    
    int k = 0;
    for(int i=0; i<N; ++i) k = max(k, colors[i] + 1);
    
    if (k < best_k) {
        best_k = k;
        for(int i=0; i<N; ++i) best_sol_color[i] = colors[i];
    }
}

// Tabu Search to find a valid k-coloring
bool solve_k(int k, double time_limit_sec, chrono::time_point<chrono::high_resolution_clock> start_time) {
    memset(adj_colors, 0, sizeof(adj_colors));
    memset(conflicts, 0, sizeof(conflicts));
    memset(tabu, 0, sizeof(tabu));
    total_conflicts = 0;
    iter_cnt = 0;
    
    // Initialize based on best solution (which has k+1 colors)
    // Identify smallest color class in best_sol_color to disperse
    vector<int> counts(best_k, 0);
    for(int i=0; i<N; ++i) counts[best_sol_color[i]]++;
    
    int min_class = 0;
    for(int c=1; c<best_k; ++c) if(counts[c] < counts[min_class]) min_class = c;
    
    // Map best_k colors to k colors
    vector<int> map_col(best_k);
    int t = 0;
    for(int c=0; c<best_k; ++c) {
        if (c == min_class) map_col[c] = -1;
        else map_col[c] = t++;
    }
    
    for(int u=0; u<N; ++u) {
        int old = best_sol_color[u];
        if (map_col[old] != -1 && map_col[old] < k) {
            current_color[u] = map_col[old];
        } else {
            current_color[u] = uniform_int_distribution<int>(0, k-1)(rng);
        }
    }
    
    // Calculate initial conflicts
    for(int u=0; u<N; ++u) {
        for(int v : adj[u]) {
            adj_colors[u][current_color[v]]++;
        }
    }
    
    for(int u=0; u<N; ++u) {
        int c = current_color[u];
        conflicts[u] = adj_colors[u][c];
        total_conflicts += conflicts[u];
    }
    total_conflicts /= 2;
    
    if (total_conflicts == 0) return true;

    while (true) {
        // Time check
        if ((iter_cnt & 1023) == 0) {
            auto now = chrono::high_resolution_clock::now();
            double elapsed = chrono::duration<double>(now - start_time).count();
            if (elapsed > time_limit_sec) return false;
        }

        int conflict_nodes_cnt = 0;
        vector<int> conflicting_nodes; 
        conflicting_nodes.reserve(N);
        for(int i=0; i<N; ++i) {
            if (conflicts[i] > 0) {
                conflicting_nodes.push_back(i);
                conflict_nodes_cnt++;
            }
        }
        
        if (conflict_nodes_cnt == 0) return true;
        
        // Dynamic Tabu Tenure
        int tenure = 0.6 * conflict_nodes_cnt + (uniform_int_distribution<int>(0, 9)(rng));
        
        int best_delta = 1e9;
        int best_u = -1;
        int best_c = -1;
        int num_candidates = 0;

        int best_tabu_delta = 1e9;
        int best_tabu_u = -1;
        int best_tabu_c = -1;
        int num_tabu_candidates = 0;

        // Evaluate moves
        for (int u : conflicting_nodes) {
            int old_c = current_color[u];
            for (int c = 0; c < k; ++c) {
                if (c == old_c) continue;
                
                int delta = adj_colors[u][c] - adj_colors[u][old_c];
                
                // Aspiration: found valid solution
                if (total_conflicts + delta == 0) {
                    best_u = u; best_c = c; best_delta = delta;
                    goto apply_move;
                }
                
                if (tabu[u][c] <= iter_cnt) {
                    // Non-tabu move
                    if (delta < best_delta) {
                        best_delta = delta;
                        best_u = u;
                        best_c = c;
                        num_candidates = 1;
                    } else if (delta == best_delta) {
                        num_candidates++;
                        if (uniform_int_distribution<int>(0, num_candidates-1)(rng) == 0) {
                            best_u = u;
                            best_c = c;
                        }
                    }
                } else {
                    // Tabu move
                    if (delta < best_tabu_delta) {
                        best_tabu_delta = delta;
                        best_tabu_u = u;
                        best_tabu_c = c;
                        num_tabu_candidates = 1;
                    } else if (delta == best_tabu_delta) {
                        num_tabu_candidates++;
                         if (uniform_int_distribution<int>(0, num_tabu_candidates-1)(rng) == 0) {
                            best_tabu_u = u;
                            best_tabu_c = c;
                        }
                    }
                }
            }
        }
        
        // Select best move
        if (best_u == -1) {
            if (best_tabu_u != -1) {
                best_u = best_tabu_u;
                best_c = best_tabu_c;
                best_delta = best_tabu_delta;
            } else {
                // Should technically not be reached unless stuck completely
                if (!conflicting_nodes.empty()) {
                    best_u = conflicting_nodes[uniform_int_distribution<int>(0, conflicting_nodes.size()-1)(rng)];
                    do {
                        best_c = uniform_int_distribution<int>(0, k-1)(rng);
                    } while(best_c == current_color[best_u]);
                    best_delta = adj_colors[best_u][best_c] - adj_colors[best_u][current_color[best_u]];
                } else {
                    break;
                }
            }
        }
        
        apply_move:
        int old_c = current_color[best_u];
        int new_c = best_c;
        current_color[best_u] = new_c;
        total_conflicts += best_delta;
        
        // Update data structures
        conflicts[best_u] += best_delta;
        for (int v : adj[best_u]) {
            adj_colors[v][old_c]--;
            adj_colors[v][new_c]++;
            if (current_color[v] == old_c) conflicts[v]--;
            if (current_color[v] == new_c) conflicts[v]++;
        }
        
        tabu[best_u][old_c] = iter_cnt + tenure;
        iter_cnt++;
        
        if (iter_cnt > 3000000) return false;
    }
    return true;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    auto start_time = chrono::high_resolution_clock::now();
    
    read_input();
    
    // 1. Initial solution with DSatur
    run_dsatur();
    
    // 2. Try simple random greedy restarts to potentially find a better starting point
    for(int rep=0; rep<15; ++rep) {
        vector<int> p(N);
        for(int i=0; i<N; ++i) p[i] = i;
        shuffle(p.begin(), p.end(), rng);
        
        vector<int> c(N, -1);
        int max_c = 0;
        for(int u : p) {
            vector<bool> used(N, false);
            for(int v : adj[u]) {
                if(c[v] != -1 && c[v] < N) used[c[v]] = true;
            }
            int col = 0;
            while(col < N && used[col]) col++;
            c[u] = col;
            max_c = max(max_c, col + 1);
        }
        
        if(max_c < best_k) {
            best_k = max_c;
            for(int i=0; i<N; ++i) best_sol_color[i] = c[i];
        }
        // Time check for initialization phase
        auto now = chrono::high_resolution_clock::now();
        if (chrono::duration<double>(now - start_time).count() > 0.3) break;
    }
    
    // 3. Tabu Search optimization loop
    while (best_k > 1) {
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - start_time).count();
        if (elapsed > 1.85) break; 
        
        // Try to solve for best_k - 1 colors
        bool success = solve_k(best_k - 1, 1.9, start_time);
        
        if (success) {
            best_k--;
            for(int i=0; i<N; ++i) best_sol_color[i] = current_color[i];
        } else {
            // Cannot find better solution in time
            break;
        }
    }
    
    for(int i=0; i<N; ++i) {
        cout << best_sol_color[i] + 1 << "\n";
    }
    
    return 0;
}