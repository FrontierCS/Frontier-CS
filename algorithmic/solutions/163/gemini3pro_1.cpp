#include <iostream>
#include <vector>
#include <queue>
#include <tuple>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Constants
const int N = 50;
const int M = 100;

// Directions
const int DR[] = {-1, 1, 0, 0};
const int DC[] = {0, 0, -1, 1};

// Global variables for best solution
vector<vector<int>> best_map;
int best_score = -1;

// Function to check if a cell is within bounds
inline bool is_valid(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < N;
}

// Connectivity check using BFS
// Returns true if removing (rem_r, rem_c) keeps region K connected
// This function verifies that all neighbors of (rem_r, rem_c) belonging to K
// can still reach each other through other cells of K.
bool check_connectivity(const vector<vector<int>>& grid, int K, int rem_r, int rem_c) {
    vector<pair<int, int>> k_neighbors;
    for (int i = 0; i < 4; ++i) {
        int nr = rem_r + DR[i];
        int nc = rem_c + DC[i];
        if (is_valid(nr, nc) && grid[nr][nc] == K) {
            k_neighbors.push_back({nr, nc});
        }
    }

    // If there are 0 or 1 neighbors, connectivity is trivially preserved (assuming size > 1 checked before)
    if (k_neighbors.size() <= 1) return true;

    int start_r = k_neighbors[0].first;
    int start_c = k_neighbors[0].second;

    static int vis[N][N];
    static int vis_token = 0;
    vis_token++;
    // Handle overflow (though unlikely in time limit)
    if(vis_token <= 0) { 
        for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) vis[i][j] = 0;
        vis_token = 1;
    }

    queue<pair<int, int>> q;
    q.push({start_r, start_c});
    vis[start_r][start_c] = vis_token;
    
    // We run BFS from one neighbor and see if we can reach all other neighbors
    
    while(!q.empty()){
        pair<int, int> curr = q.front();
        q.pop();
        
        for(int i=0; i<4; ++i){
            int nr = curr.first + DR[i];
            int nc = curr.second + DC[i];
            
            // Traverse K cells, skip the one being removed
            if(is_valid(nr, nc) && grid[nr][nc] == K && !(nr == rem_r && nc == rem_c)){
                if(vis[nr][nc] != vis_token){
                    vis[nr][nc] = vis_token;
                    q.push({nr, nc});
                }
            }
        }
    }
    
    // Check if all K-neighbors were visited
    for(size_t i = 1; i < k_neighbors.size(); ++i){
        if(vis[k_neighbors[i].first][k_neighbors[i].second] != vis_token) return false;
    }
    
    return true;
}

void solve() {
    int n_in, m_in;
    if (!(cin >> n_in >> m_in)) return;
    
    vector<vector<int>> initial_grid(N, vector<int>(N));
    vector<int> component_size(M + 1, 0);
    // S0 stores regions that touch the boundary in the initial map
    // Only these regions are allowed to be adjacent to 0 in the output map
    vector<bool> s0(M + 1, false);
    
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> initial_grid[i][j];
            component_size[initial_grid[i][j]]++;
            if (i == 0 || i == N - 1 || j == 0 || j == N - 1) {
                s0[initial_grid[i][j]] = true;
            }
        }
    }

    // Compute initial contact counts (number of edges between different regions)
    int contact_count[M + 1][M + 1];
    for(int i=0; i<=M; ++i)
        for(int j=0; j<=M; ++j)
            contact_count[i][j] = 0;

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            int u = initial_grid[i][j];
            for (int k = 0; k < 4; ++k) {
                int ni = i + DR[k];
                int nj = j + DC[k];
                if (is_valid(ni, nj)) {
                    int v = initial_grid[ni][nj];
                    if (u < v) {
                        contact_count[u][v]++;
                        contact_count[v][u]++;
                    }
                }
            }
        }
    }

    best_map = initial_grid;
    best_score = 0;

    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.90; // Limit execution to just under 2 seconds

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    // Iterative optimization loop
    while (true) {
        auto current_time = chrono::steady_clock::now();
        chrono::duration<double> elapsed = current_time - start_time;
        if (elapsed.count() > time_limit) break;

        // Start with a fresh copy of the grid
        vector<vector<int>> grid = initial_grid;
        vector<int> cur_comp_size = component_size;
        
        int cur_contact[M + 1][M + 1];
        for(int i=1; i<=M; ++i)
            for(int j=1; j<=M; ++j)
                cur_contact[i][j] = contact_count[i][j];
        
        // Candidates for removal: cells currently adjacent to 0 (or boundary)
        vector<pair<int, int>> candidates;
        vector<vector<bool>> in_candidates(N, vector<bool>(N, false));

        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (i == 0 || i == N - 1 || j == 0 || j == N - 1) {
                    candidates.push_back({i, j});
                    in_candidates[i][j] = true;
                }
            }
        }

        int current_zeros = 0;
        
        // Greedily remove cells
        while (!candidates.empty()) {
            // Pick a random candidate
            int idx = uniform_int_distribution<int>(0, candidates.size() - 1)(rng);
            pair<int, int> p = candidates[idx];
            
            // Remove from list efficiently
            candidates[idx] = candidates.back();
            candidates.pop_back();
            in_candidates[p.first][p.second] = false;

            int r = p.first;
            int c = p.second;
            int K = grid[r][c];

            if (K == 0) continue;
            
            // Condition 0: Only regions in S0 can touch 0
            // Since we are eroding from boundary, any removed cell exposes neighbors to 0
            // So we can only remove cells of color K if K is allowed to touch 0.
            if (!s0[K]) continue;

            // Gather non-zero neighbors
            vector<int> neighbors_colors;
            for(int k=0; k<4; ++k) {
                int nr = r + DR[k];
                int nc = c + DC[k];
                if(is_valid(nr, nc)) {
                    int L = grid[nr][nc];
                    if(L != 0 && L != K) {
                        neighbors_colors.push_back(L);
                    }
                }
            }
            
            bool possible = true;
            // Condition 2a: Neighbors exposed to 0 must be in S0
            for(int L : neighbors_colors) {
                if(!s0[L]) {
                    possible = false;
                    break;
                }
            }
            if(!possible) continue;

            // Condition 2b: Adjacencies must be preserved
            // We count how many contact edges we are removing
            vector<pair<int, int>> reductions;
            for(int L : neighbors_colors) {
                bool found = false;
                for(auto& pair : reductions) {
                    if(pair.first == L) {
                        pair.second++;
                        found = true;
                        break;
                    }
                }
                if(!found) reductions.push_back({L, 1});
            }

            for(auto& pair : reductions) {
                // Must leave at least one edge between K and L
                if(cur_contact[K][pair.first] - pair.second <= 0) {
                    possible = false;
                    break;
                }
            }
            if(!possible) continue;

            // Condition 4: Region size must remain > 0 (actually > 1 if we remove one)
            // If size is 1, removing makes it 0 -> region disappears, invalid.
            if(cur_comp_size[K] <= 1) continue;
            
            // Condition 3: Connectivity check
            if(!check_connectivity(grid, K, r, c)) continue;

            // All checks passed, perform removal
            grid[r][c] = 0;
            cur_comp_size[K]--;
            current_zeros++;
            
            // Update contact counts
            for(auto& pair : reductions) {
                cur_contact[K][pair.first] -= pair.second;
                cur_contact[pair.first][K] -= pair.second;
            }

            // Add newly exposed neighbors to candidates
            for (int k = 0; k < 4; ++k) {
                int nr = r + DR[k];
                int nc = c + DC[k];
                if (is_valid(nr, nc)) {
                    int L = grid[nr][nc];
                    if (L != 0) {
                        if (!in_candidates[nr][nc]) {
                            candidates.push_back({nr, nc});
                            in_candidates[nr][nc] = true;
                        }
                    }
                }
            }
        }

        if (current_zeros > best_score) {
            best_score = current_zeros;
            best_map = grid;
        }
    }

    // Output best map found
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cout << best_map[i][j] << (j == N - 1 ? "" : " ");
        }
        cout << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}