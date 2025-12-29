#include <iostream>
#include <vector>
#include <queue>
#include <set>
#include <map>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

const int N = 50;
const int M = 100;
int original_map[N][N];
int current_map[N][N];
bool target_adj[M + 1][M + 1];
int edge_counts[M + 1][M + 1];
int area_size[M + 1];

int dr[] = {0, 0, 1, -1};
int dc[] = {1, -1, 0, 0};

bool is_valid(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < N;
}

// Check if removing (r, c) (changing color k -> 0) breaks connectivity of k
bool check_connectivity_remove(int r, int c, int k) {
    if (area_size[k] <= 1) return false;

    int start_r = -1, start_c = -1;
    for (int i = 0; i < 4; ++i) {
        int nr = r + dr[i];
        int nc = c + dc[i];
        if (is_valid(nr, nc) && current_map[nr][nc] == k) {
            start_r = nr;
            start_c = nc;
            break;
        }
    }
    
    if (start_r == -1) return false; 

    int count = 0;
    static int visited_token[N][N];
    static int token = 0;
    token++;
    
    queue<pair<int, int>> q;
    q.push({start_r, start_c});
    visited_token[start_r][start_c] = token;
    count++;
    
    while (!q.empty()) {
        pair<int, int> p = q.front();
        q.pop();
        
        for (int i = 0; i < 4; ++i) {
            int nr = p.first + dr[i];
            int nc = p.second + dc[i];
            if (is_valid(nr, nc) && current_map[nr][nc] == k && !(nr == r && nc == c)) {
                if (visited_token[nr][nc] != token) {
                    visited_token[nr][nc] = token;
                    count++;
                    q.push({nr, nc});
                }
            }
        }
    }
    
    return count == area_size[k] - 1;
}

// Check if adding (r, c) (changing 0 -> k) breaks connectivity of 0
bool check_connectivity_add(int r, int c) {
    int reachable = 0;
    static int visited_token[N][N];
    static int token = 0;
    token++;
    
    queue<pair<int, int>> q;
    
    // Add all boundary 0s to queue
    for (int i = 0; i < N; ++i) {
        if (current_map[0][i] == 0 && !(0 == r && i == c) && visited_token[0][i] != token) {
            visited_token[0][i] = token; q.push({0, i}); reachable++;
        }
        if (current_map[N-1][i] == 0 && !(N-1 == r && i == c) && visited_token[N-1][i] != token) {
            visited_token[N-1][i] = token; q.push({N-1, i}); reachable++;
        }
        if (current_map[i][0] == 0 && !(i == r && 0 == c) && visited_token[i][0] != token) {
            visited_token[i][0] = token; q.push({i, 0}); reachable++;
        }
        if (current_map[i][N-1] == 0 && !(i == r && N-1 == c) && visited_token[i][N-1] != token) {
            visited_token[i][N-1] = token; q.push({i, N-1}); reachable++;
        }
    }

    while (!q.empty()) {
        pair<int, int> p = q.front();
        q.pop();
        
        for (int i = 0; i < 4; ++i) {
            int nr = p.first + dr[i];
            int nc = p.second + dc[i];
            
            if (is_valid(nr, nc) && current_map[nr][nc] == 0 && !(nr == r && nc == c)) {
                if (visited_token[nr][nc] != token) {
                    visited_token[nr][nc] = token;
                    reachable++;
                    q.push({nr, nc});
                }
            }
        }
    }
    
    return reachable == area_size[0] - 1;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n_in, m_in;
    if (!(cin >> n_in >> m_in)) return 0;
    
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> original_map[i][j];
            current_map[i][j] = original_map[i][j];
            area_size[current_map[i][j]]++;
        }
    }

    // Build target adjacency and initial edge counts
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            int u = original_map[i][j];
            
            if (i == 0 || i == N - 1 || j == 0 || j == N - 1) {
                target_adj[u][0] = true;
                if (i == 0) edge_counts[u][0]++;
                if (i == N - 1) edge_counts[u][0]++;
                if (j == 0) edge_counts[u][0]++;
                if (j == N - 1) edge_counts[u][0]++;
            }
            
            for (int k = 0; k < 4; ++k) {
                int ni = i + dr[k];
                int nj = j + dc[k];
                if (is_valid(ni, nj)) {
                    int v = original_map[ni][nj];
                    if (u != v) {
                        target_adj[u][v] = true;
                        edge_counts[u][v]++;
                    }
                }
            }
        }
    }
    
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.95; 
    
    mt19937 rng(12345);
    uniform_int_distribution<int> dist_coord(0, N - 1);
    uniform_real_distribution<double> dist_prob(0.0, 1.0);

    double T_start = 2.0;
    double T_end = 0.05;
    
    int iter = 0;
    while (true) {
        if ((iter & 1023) == 0) {
            auto curr_time = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(curr_time - start_time).count();
            if (elapsed > time_limit) break;
        }
        
        int r = dist_coord(rng);
        int c = dist_coord(rng);
        
        int current_color = current_map[r][c];
        
        if (current_color != 0) {
            if (!target_adj[current_color][0]) continue;
            
            bool adj_ok = true;
            int lost_edges[M + 1] = {0}; 
            int lost_edges_0 = 0; 
            
            if (r == 0) lost_edges_0++;
            if (r == N - 1) lost_edges_0++;
            if (c == 0) lost_edges_0++;
            if (c == N - 1) lost_edges_0++;
            
            for (int k = 0; k < 4; ++k) {
                int nr = r + dr[k];
                int nc = c + dc[k];
                if (is_valid(nr, nc)) {
                    int n_color = current_map[nr][nc];
                    if (n_color != current_color) {
                        if (n_color == 0) lost_edges_0++;
                        else lost_edges[n_color]++;
                    }
                }
            }
            
            if (edge_counts[current_color][0] - lost_edges_0 <= 0) adj_ok = false;
            else {
                for (int k = 1; k <= M; ++k) {
                    if (lost_edges[k] > 0) {
                        if (edge_counts[current_color][k] - lost_edges[k] <= 0) {
                            adj_ok = false;
                            break;
                        }
                    }
                }
            }
            
            if (adj_ok) {
                for (int k = 0; k < 4; ++k) {
                    int nr = r + dr[k];
                    int nc = c + dc[k];
                    if (is_valid(nr, nc)) {
                        int n_color = current_map[nr][nc];
                        if (n_color != 0 && n_color != current_color) {
                            if (!target_adj[n_color][0]) {
                                adj_ok = false;
                                break;
                            }
                        }
                    }
                }
            }
            
            if (!adj_ok) continue;
            if (!check_connectivity_remove(r, c, current_color)) continue;
            
            current_map[r][c] = 0;
            area_size[current_color]--;
            area_size[0]++;
            
            edge_counts[current_color][0] -= lost_edges_0;
            for (int k = 1; k <= M; ++k) {
                if (lost_edges[k] > 0) edge_counts[current_color][k] -= lost_edges[k];
            }
            
            for (int k = 0; k < 4; ++k) {
                int nr = r + dr[k];
                int nc = c + dc[k];
                if (is_valid(nr, nc)) {
                    int n_color = current_map[nr][nc]; 
                    if (n_color != 0) {
                        edge_counts[n_color][0]++;
                        edge_counts[0][n_color]++;
                    }
                }
            }
            
        } else {
            auto curr_time_p = chrono::steady_clock::now();
            double el = chrono::duration<double>(curr_time_p - start_time).count();
            double T = T_start + (T_end - T_start) * (el / time_limit);
            if (dist_prob(rng) > exp(-1.0 / T)) continue;
            
            int target = original_map[r][c];
            
            bool adj_target = false;
            for (int k = 0; k < 4; ++k) {
                int nr = r + dr[k];
                int nc = c + dc[k];
                if (is_valid(nr, nc) && current_map[nr][nc] == target) {
                    adj_target = true; break;
                }
            }
            if (!adj_target) continue;
            
            bool adj_ok = true;
            int lost_edges_0[M + 1] = {0}; 
            
            for (int k = 0; k < 4; ++k) {
                int nr = r + dr[k];
                int nc = c + dc[k];
                if (is_valid(nr, nc)) {
                    int n_color = current_map[nr][nc];
                    if (n_color != 0) {
                        lost_edges_0[n_color]++;
                    }
                }
            }
            
            for (int k = 1; k <= M; ++k) {
                if (lost_edges_0[k] > 0) {
                    if (target_adj[k][0] && edge_counts[k][0] - lost_edges_0[k] <= 0) {
                        adj_ok = false; break;
                    }
                }
            }
            if (!adj_ok) continue;
            
            if (!check_connectivity_add(r, c)) continue;
            
            current_map[r][c] = target;
            area_size[0]--;
            area_size[target]++;
            
            for (int k = 1; k <= M; ++k) {
                if (lost_edges_0[k] > 0) {
                    edge_counts[k][0] -= lost_edges_0[k];
                    edge_counts[0][k] -= lost_edges_0[k];
                }
            }
            
            int new_edges_0_for_target = 0;
            if (r == 0) new_edges_0_for_target++;
            if (r == N - 1) new_edges_0_for_target++;
            if (c == 0) new_edges_0_for_target++;
            if (c == N - 1) new_edges_0_for_target++;
            
            for (int k = 0; k < 4; ++k) {
                int nr = r + dr[k];
                int nc = c + dc[k];
                if (is_valid(nr, nc)) {
                    int n_color = current_map[nr][nc];
                    if (n_color != target) {
                        if (n_color == 0) new_edges_0_for_target++;
                        else {
                            edge_counts[target][n_color]++;
                            edge_counts[n_color][target]++;
                        }
                    }
                }
            }
            edge_counts[target][0] += new_edges_0_for_target;
            edge_counts[0][target] += new_edges_0_for_target;
        }
        
        iter++;
    }
    
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cout << current_map[i][j] << (j == N - 1 ? "" : " ");
        }
        cout << "\n";
    }

    return 0;
}