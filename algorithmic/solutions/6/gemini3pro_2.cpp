#include <vector>
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <algorithm>
#include <iostream>

namespace Solver {

using namespace std;

int N_val, M_val;
vector<pair<int, int>> edges;
bool adj[45][45];
vector<int> adj_list[45];

struct State {
    int K;
    vector<vector<int>> grid;
    int color_counts[45];
    int edge_counts[45][45]; 
    int realized_edge_count;
    int present_color_count;

    void init(int k, int n) {
        K = k;
        grid.assign(K, vector<int>(K, 1));
        for(int i=0; i<=n; ++i) color_counts[i] = 0;
        for(int i=0; i<=n; ++i)
            for(int j=0; j<=n; ++j) edge_counts[i][j] = 0;
        
        realized_edge_count = 0;
        present_color_count = 0;
        
        // Initial grid is all 1s
        color_counts[1] = K * K;
        present_color_count = 1;
    }

    bool is_valid_change(int r, int c, int new_color) {
        int dr[] = {-1, 1, 0, 0};
        int dc[] = {0, 0, -1, 1};
        for(int i=0; i<4; ++i) {
            int nr = r + dr[i];
            int nc = c + dc[i];
            if(nr >= 0 && nr < K && nc >= 0 && nc < K) {
                int neighbor_color = grid[nr][nc];
                if(neighbor_color != new_color) {
                    if(!adj[new_color][neighbor_color]) return false;
                }
            }
        }
        return true;
    }

    void apply_change(int r, int c, int new_color) {
        int old_color = grid[r][c];
        if(old_color == new_color) return;

        int dr[] = {-1, 1, 0, 0};
        int dc[] = {0, 0, -1, 1};

        // Remove old adjacencies
        for(int i=0; i<4; ++i) {
            int nr = r + dr[i];
            int nc = c + dc[i];
            if(nr >= 0 && nr < K && nc >= 0 && nc < K) {
                int neighbor = grid[nr][nc];
                if(neighbor != old_color) {
                    int u = min(old_color, neighbor);
                    int v = max(old_color, neighbor);
                    if(adj[u][v]) {
                        edge_counts[u][v]--;
                        if(edge_counts[u][v] == 0) realized_edge_count--;
                    }
                }
            }
        }

        color_counts[old_color]--;
        if(color_counts[old_color] == 0) present_color_count--;

        grid[r][c] = new_color;
        color_counts[new_color]++;
        if(color_counts[new_color] == 1) present_color_count++;

        // Add new adjacencies
        for(int i=0; i<4; ++i) {
            int nr = r + dr[i];
            int nc = c + dc[i];
            if(nr >= 0 && nr < K && nc >= 0 && nc < K) {
                int neighbor = grid[nr][nc];
                if(neighbor != new_color) {
                    int u = min(new_color, neighbor);
                    int v = max(new_color, neighbor);
                    if(adj[u][v]) {
                        if(edge_counts[u][v] == 0) realized_edge_count++;
                        edge_counts[u][v]++;
                    }
                }
            }
        }
    }
};

vector<vector<int>> solve_for_K(int N, int M, int K, double time_limit_sec) {
    State state;
    state.init(K, N);
    
    clock_t start_time = clock();
    int max_iter = 10000000; 

    for(int iter=0; iter<max_iter; ++iter) {
        if((iter & 511) == 0) {
            double elapsed = (double)(clock() - start_time) / CLOCKS_PER_SEC;
            if(elapsed > time_limit_sec) return {};
            if(state.present_color_count == N && state.realized_edge_count == M) {
                return state.grid;
            }
        }

        bool missing_color = (state.present_color_count < N);
        
        if (missing_color) {
            int target = -1;
            vector<int> missing;
            for(int c=1; c<=N; ++c) if(state.color_counts[c] == 0) missing.push_back(c);
            if(!missing.empty()) target = missing[rand() % missing.size()];
            
            if(target != -1) {
                bool found_friend = false;
                for(int neighbor : adj_list[target]) {
                    if(state.color_counts[neighbor] > 0) {
                        found_friend = true;
                        break;
                    }
                }
                
                bool moved = false;
                int attempts = 50; 
                while(attempts--) {
                    int r = rand() % K;
                    int c = rand() % K;
                    if(state.is_valid_change(r, c, target)) {
                        bool connects = false;
                        if(found_friend) {
                             int dr[] = {-1, 1, 0, 0};
                             int dc[] = {0, 0, -1, 1};
                             for(int d=0; d<4; ++d) {
                                 int nr = r + dr[d], nc = c + dc[d];
                                 if(nr>=0 && nr<K && nc>=0 && nc<K) {
                                     if(adj[target][state.grid[nr][nc]]) {
                                         connects = true; break;
                                     }
                                 }
                             }
                        } else {
                            connects = true; 
                        }
                        
                        if(connects) {
                            state.apply_change(r, c, target);
                            moved = true;
                            break;
                        }
                    }
                }
                if(moved) continue;
                
                 attempts = 20;
                 while(attempts--) {
                     int r = rand() % K;
                     int c = rand() % K;
                     if(state.is_valid_change(r, c, target)) {
                         state.apply_change(r, c, target);
                         break;
                     }
                 }
                 continue;
            }
        }

        if(state.realized_edge_count < M) {
             vector<pair<int, int>> missing_edges;
             for(auto& e : edges) {
                 if(state.edge_counts[e.first][e.second] == 0) {
                     missing_edges.push_back(e);
                 }
             }
             if(!missing_edges.empty()) {
                 auto target_edge = missing_edges[rand() % missing_edges.size()];
                 int u = target_edge.first;
                 int v = target_edge.second;
                 
                 bool u_exists = state.color_counts[u] > 0;
                 bool v_exists = state.color_counts[v] > 0;
                 
                 if(u_exists && v_exists) {
                     bool success = false;
                     int tries = 50;
                     while(tries--) {
                         int r = rand() % K;
                         int c = rand() % K;
                         int current = state.grid[r][c];
                         if(current == u) {
                             int dr[] = {-1, 1, 0, 0};
                             int dc[] = {0, 0, -1, 1};
                             int d = rand() % 4;
                             int nr = r + dr[d], nc = c + dc[d];
                             if(nr>=0 && nr<K && nc>=0 && nc<K) {
                                 if(state.is_valid_change(nr, nc, v)) {
                                     state.apply_change(nr, nc, v);
                                     success = true;
                                     break;
                                 }
                             }
                         } else if (current == v) {
                             int dr[] = {-1, 1, 0, 0};
                             int dc[] = {0, 0, -1, 1};
                             int d = rand() % 4;
                             int nr = r + dr[d], nc = c + dc[d];
                             if(nr>=0 && nr<K && nc>=0 && nc<K) {
                                 if(state.is_valid_change(nr, nc, u)) {
                                     state.apply_change(nr, nc, u);
                                     success = true;
                                     break;
                                 }
                             }
                         }
                     }
                     if(success) continue;
                 }
             }
        }
        
        int r = rand() % K;
        int c = rand() % K;
        
        vector<int> valid_colors;
        valid_colors.reserve(N);
        for(int clr=1; clr<=N; ++clr) {
            if(state.is_valid_change(r, c, clr)) {
                valid_colors.push_back(clr);
            }
        }
        
        if(!valid_colors.empty()) {
            int best_c = -1;
            int best_gain = -10000;
            
            if(valid_colors.size() > 5) {
                for(int i=0; i<5; ++i) {
                    swap(valid_colors[i], valid_colors[i + rand()%(valid_colors.size()-i)]);
                }
                valid_colors.resize(5);
            }

            for(int clr : valid_colors) {
                if(clr == state.grid[r][c]) continue;
                int gain = 0;
                if(state.color_counts[clr] == 0) gain += 1000;
                if(state.color_counts[state.grid[r][c]] == 1) gain -= 1000;
                
                int dr[] = {-1, 1, 0, 0};
                int dc[] = {0, 0, -1, 1};
                for(int i=0; i<4; ++i) {
                    int nr = r + dr[i], nc = c + dc[i];
                    if(nr>=0 && nr<K && nc>=0 && nc<K) {
                        int n_clr = state.grid[nr][nc];
                        if(n_clr != clr) {
                             int u = min(clr, n_clr);
                             int v = max(clr, n_clr);
                             if(adj[u][v] && state.edge_counts[u][v] == 0) gain += 100;
                        }
                    }
                }
                int old_c = state.grid[r][c];
                for(int i=0; i<4; ++i) {
                    int nr = r + dr[i], nc = c + dc[i];
                    if(nr>=0 && nr<K && nc>=0 && nc<K) {
                        int n_clr = state.grid[nr][nc];
                        if(n_clr != old_c) {
                             int u = min(old_c, n_clr);
                             int v = max(old_c, n_clr);
                             if(adj[u][v] && state.edge_counts[u][v] == 1) gain -= 100;
                        }
                    }
                }
                
                if(gain > best_gain) {
                    best_gain = gain;
                    best_c = clr;
                }
            }
            
            if(best_c != -1) {
                if(best_gain >= 0 || (rand() % 20 == 0)) 
                    state.apply_change(r, c, best_c);
            }
        }
    }
    
    return {};
}

} 

std::vector<std::vector<int>> create_map(int N, int M,
    std::vector<int> A, std::vector<int> B) {
    
    using namespace Solver;
    N_val = N;
    M_val = M;
    for(int i=0; i<=N; ++i) {
        adj_list[i].clear();
        for(int j=0; j<=N; ++j) adj[i][j] = false;
    }
    edges.clear();
    for(int i=0; i<M; ++i) {
        adj[A[i]][B[i]] = adj[B[i]][A[i]] = true;
        adj_list[A[i]].push_back(B[i]);
        adj_list[B[i]].push_back(A[i]);
        edges.push_back({min(A[i], B[i]), max(A[i], B[i])});
    }

    srand(12345); 
    
    int K1 = max((int)ceil(sqrt(N)) + 2, N/2);
    if(K1 >= N) K1 = 0; 
    
    if(K1 > 0) {
        vector<vector<int>> res = solve_for_K(N, M, K1, 0.5); 
        if(!res.empty()) return res;
    }
    
    int K2 = max(K1 + 1, (int)(N * 0.75));
    if(K2 >= N) K2 = 0;
     if(K2 > 0) {
        vector<vector<int>> res = solve_for_K(N, M, K2, 0.5); 
        if(!res.empty()) return res;
    }

    vector<vector<int>> res = solve_for_K(N, M, min(N, 240), 1.9);
    if(!res.empty()) return res;
    
    vector<vector<int>> dummy(N, vector<int>(N, 1));
    for(int i=0; i<N; ++i) dummy[i][i] = i+1; 
    return dummy;
}