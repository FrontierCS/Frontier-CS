#include <iostream>
#include <vector>
#include <cstring>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Constants
const int N = 50;
const int PN = N + 2; // Padded size
const double TIME_LIMIT = 1.95;

// Global variables
int n, m;
int initial_grid[PN][PN];
int current_grid[PN][PN];
int best_grid[PN][PN];
int best_score = -1;

// Adjacency requirements from input
bool required_adj[101][101];

// Dynamic state
int adj_counts[101][101]; // adj_counts[u][v] = number of adjacent pairs of cells with colors u and v
int region_size[101];     // Number of cells of each color

// Directions
const int dr[] = {0, 0, 1, -1};
const int dc[] = {1, -1, 0, 0};

// Random engine
mt19937 rng(12345);

// Helper for timing
double get_time() {
    static auto start_time = chrono::steady_clock::now();
    auto now = chrono::steady_clock::now();
    return chrono::duration<double>(now - start_time).count();
}

void read_input() {
    cin >> n >> m;
    memset(initial_grid, 0, sizeof(initial_grid));
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cin >> initial_grid[i][j];
        }
    }
}

void compute_required_adj() {
    memset(required_adj, 0, sizeof(required_adj));
    for (int i = 0; i < PN; ++i) {
        for (int j = 0; j < PN; ++j) {
            int c1 = initial_grid[i][j];
            // Check right and down neighbors
            if (j + 1 < PN) {
                int c2 = initial_grid[i][j + 1];
                if (c1 != c2) {
                    required_adj[c1][c2] = true;
                    required_adj[c2][c1] = true;
                }
            }
            if (i + 1 < PN) {
                int c2 = initial_grid[i + 1][j];
                if (c1 != c2) {
                    required_adj[c1][c2] = true;
                    required_adj[c2][c1] = true;
                }
            }
        }
    }
}

void init_state() {
    memcpy(current_grid, initial_grid, sizeof(initial_grid));
    memset(adj_counts, 0, sizeof(adj_counts));
    memset(region_size, 0, sizeof(region_size));
    
    for (int i = 0; i < PN; ++i) {
        for (int j = 0; j < PN; ++j) {
            int c = current_grid[i][j];
            if (c != 0) region_size[c]++;
            
            if (j + 1 < PN) {
                int c2 = current_grid[i][j + 1];
                if (c != c2) {
                    adj_counts[c][c2]++;
                    adj_counts[c2][c]++;
                }
            }
            if (i + 1 < PN) {
                int c2 = current_grid[i + 1][j];
                if (c != c2) {
                    adj_counts[c][c2]++;
                    adj_counts[c2][c]++;
                }
            }
        }
    }
}

// BFS to check if removing (r, c) disconnects region k
// Returns true if connected
bool check_connectivity(int r, int c, int k) {
    if (region_size[k] <= 1) return false; 
    
    // Find a starting neighbor of color k
    int start_r = -1, start_c = -1;
    int neighbors_k = 0;
    
    for (int i = 0; i < 4; ++i) {
        int nr = r + dr[i];
        int nc = c + dc[i];
        // Boundary check strictly not needed due to padding and logic
        if (current_grid[nr][nc] == k) {
            if (start_r == -1) {
                start_r = nr;
                start_c = nc;
            }
            neighbors_k++;
        }
    }
    
    if (neighbors_k == 0) return false; // Should not happen
    if (neighbors_k == 1) return true;  // Leaf node removal is safe for connectivity
    
    // BFS
    static int q_buff[2600][2];
    static int visit_token[PN][PN];
    static int token = 0;
    token++;
    
    int q_head = 0, q_tail = 0;
    q_buff[q_tail][0] = start_r;
    q_buff[q_tail][1] = start_c;
    q_tail++;
    visit_token[start_r][start_c] = token;
    
    // Mark the removed cell as visited so BFS avoids it
    visit_token[r][c] = token;
    
    int count = 1;
    
    while(q_head < q_tail) {
        int cr = q_buff[q_head][0];
        int cc = q_buff[q_head][1];
        q_head++;
        
        for (int i = 0; i < 4; ++i) {
            int nr = cr + dr[i];
            int nc = cc + dc[i];
            if (current_grid[nr][nc] == k && visit_token[nr][nc] != token) {
                visit_token[nr][nc] = token;
                q_buff[q_tail][0] = nr;
                q_buff[q_tail][1] = nc;
                q_tail++;
                count++;
            }
        }
    }
    
    return count == region_size[k] - 1;
}

void solve() {
    read_input();
    compute_required_adj();
    
    // Initial best is input
    memcpy(best_grid, initial_grid, sizeof(initial_grid));
    best_score = 0; // Score is E+1, here we count E. E=0 initially.
    
    // Repeatedly try to erode the map
    while (get_time() < TIME_LIMIT) {
        init_state();
        
        vector<pair<int, int>> candidates;
        static bool in_cand[PN][PN];
        memset(in_cand, 0, sizeof(in_cand));
        
        // Populate initial candidates: non-0 cells adjacent to 0
        for (int i = 1; i <= n; ++i) {
            for (int j = 1; j <= n; ++j) {
                if (current_grid[i][j] != 0) {
                    bool adj0 = false;
                    for (int d = 0; d < 4; ++d) {
                        if (current_grid[i + dr[d]][j + dc[d]] == 0) {
                            adj0 = true;
                            break;
                        }
                    }
                    if (adj0) {
                        candidates.push_back({i, j});
                        in_cand[i][j] = true;
                    }
                }
            }
        }
        
        while (!candidates.empty()) {
            // Pick random candidate
            int idx = uniform_int_distribution<int>(0, candidates.size() - 1)(rng);
            pair<int, int> p = candidates[idx];
            
            // Remove from candidates (swap with back)
            candidates[idx] = candidates.back();
            candidates.pop_back();
            in_cand[p.first][p.second] = false;
            
            int r = p.first;
            int c = p.second;
            int k = current_grid[r][c];
            
            if (k == 0) continue;
            
            // --- Check Validity ---
            bool possible = true;
            
            // 1. Check Adjacency Preservation
            vector<int> lost_neighs;
            for (int d = 0; d < 4; ++d) {
                int nr = r + dr[d];
                int nc = c + dc[d];
                int neighbor_col = current_grid[nr][nc];
                if (neighbor_col != k) {
                    lost_neighs.push_back(neighbor_col);
                }
            }
            
            static int local_decr[101];
            vector<int> unique_lost;
            for (int nc : lost_neighs) {
                if (local_decr[nc] == 0) unique_lost.push_back(nc);
                local_decr[nc]++;
            }
            
            for (int nc : unique_lost) {
                if (required_adj[k][nc]) {
                    if (adj_counts[k][nc] - local_decr[nc] <= 0) {
                        possible = false;
                    }
                }
            }
            
            for (int nc : unique_lost) local_decr[nc] = 0; // Cleanup
            
            if (!possible) continue;
            
            // 2. Check Permission for New Adjacencies to 0
            // Neighbors p != 0 will become adjacent to the new 0 at (r,c)
            for (int d = 0; d < 4; ++d) {
                int nr = r + dr[d];
                int nc = c + dc[d];
                int p = current_grid[nr][nc];
                if (p != 0 && p != k) {
                    if (!required_adj[p][0]) {
                        possible = false;
                        break;
                    }
                }
            }
            if (!possible) continue;
            
            // 3. Check Connectivity of Region k
            if (!check_connectivity(r, c, k)) continue;
            
            // --- Apply Change ---
            
            // Update counts
            for (int d = 0; d < 4; ++d) {
                int nr = r + dr[d];
                int nc = c + dc[d];
                int p = current_grid[nr][nc];
                if (p != k) {
                    adj_counts[k][p]--;
                    adj_counts[p][k]--;
                }
                if (p != 0) {
                    adj_counts[p][0]++;
                    adj_counts[0][p]++;
                }
            }
            
            current_grid[r][c] = 0;
            region_size[k]--;
            
            // Add valid neighbors to candidates
            for (int d = 0; d < 4; ++d) {
                int nr = r + dr[d];
                int nc = c + dc[d];
                int p = current_grid[nr][nc];
                // Only non-0 regions can be eroded.
                // We add them if not already in candidates.
                if (p != 0 && !in_cand[nr][nc]) {
                    candidates.push_back({nr, nc});
                    in_cand[nr][nc] = true;
                }
            }
        }
        
        // Score calculation: count number of 0s inside the nxn area
        int current_score = 0;
        for (int i = 1; i <= n; ++i) {
            for (int j = 1; j <= n; ++j) {
                if (current_grid[i][j] == 0) current_score++;
            }
        }
        
        if (current_score > best_score) {
            best_score = current_score;
            memcpy(best_grid, current_grid, sizeof(current_grid));
        }
    }
    
    // Output result
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cout << best_grid[i][j] << (j == n ? "" : " ");
        }
        cout << "\n";
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}