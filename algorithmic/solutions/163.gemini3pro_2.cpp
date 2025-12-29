#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <map>
#include <cstring>
#include <cstdlib>
#include <ctime>

using namespace std;

// Global variables for problem state
int N, M;
int initial_grid[55][55];
int best_grid[55][55];
int current_grid[55][55];
int best_score = -1;

// Constraints and properties
bool is_adj_0[105]; // If color c is adjacent to boundary/0 in original map
int initial_edge_counts[105][105]; // Adjacency counts between colors
int current_edge_counts[105][105];
int current_region_size[105];

// Directions for neighbors
int dr[] = {0, 0, 1, -1};
int dc[] = {1, -1, 0, 0};

// Optimization for connectivity checks
int visited_token[55][55];
int current_token = 0;

bool in_bounds(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < N;
}

// Check if region `color` stays connected after removing (r, c)
// Uses BFS on the component
bool check_connectivity(int r, int c, int color) {
    // Identify neighbors of the same color
    vector<pair<int, int>> neighbors;
    for (int i = 0; i < 4; i++) {
        int nr = r + dr[i];
        int nc = c + dc[i];
        if (in_bounds(nr, nc) && current_grid[nr][nc] == color) {
            neighbors.push_back({nr, nc});
        }
    }

    // If 0 or 1 neighbor, connectivity is trivial (assuming size check > 1 passed)
    if (neighbors.empty()) return true; 

    // BFS starting from the first neighbor
    current_token++;
    queue<pair<int, int>> q;
    q.push(neighbors[0]);
    visited_token[neighbors[0].first][neighbors[0].second] = current_token;
    visited_token[r][c] = current_token; // Treat the removed cell as blocked
    
    while (!q.empty()) {
        pair<int, int> curr = q.front();
        q.pop();
        
        for (int i = 0; i < 4; i++) {
            int nr = curr.first + dr[i];
            int nc = curr.second + dc[i];
            if (in_bounds(nr, nc) && visited_token[nr][nc] != current_token && current_grid[nr][nc] == color) {
                visited_token[nr][nc] = current_token;
                q.push({nr, nc});
            }
        }
    }
    
    // Ensure all original neighbors were reached
    for (size_t i = 1; i < neighbors.size(); i++) {
        if (visited_token[neighbors[i].first][neighbors[i].second] != current_token) return false;
    }
    return true;
}

// Core solver function
void solve() {
    // Reset state to initial
    memcpy(current_grid, initial_grid, sizeof(initial_grid));
    memcpy(current_edge_counts, initial_edge_counts, sizeof(initial_edge_counts));
    memset(current_region_size, 0, sizeof(current_region_size));
    
    for(int i=0; i<N; ++i) 
        for(int j=0; j<N; ++j) 
            current_region_size[current_grid[i][j]]++;

    bool changed = true;
    while(changed) {
        changed = false;
        
        // Candidate list: all valid cells belonging to regions touching 0
        vector<pair<int, int>> order;
        order.reserve(N * N);
        for(int i=0; i<N; ++i) {
            for(int j=0; j<N; ++j) {
                int c = current_grid[i][j];
                if(c != 0 && is_adj_0[c]) {
                    order.push_back({i, j});
                }
            }
        }

        // Random shuffle to vary the erosion pattern
        for(int i=order.size()-1; i>0; i--) {
            int j = rand() % (i+1);
            swap(order[i], order[j]);
        }
        
        for(auto p : order) {
            int r = p.first;
            int c = p.second;
            int color = current_grid[r][c];
            
            if(color == 0) continue; // Already removed in this pass
            
            // 1. Must be adjacent to 0 (boundary or 0-cell) to erode from outside
            bool adj_0 = false;
            for(int k=0; k<4; ++k) {
                int nr = r + dr[k];
                int nc = c + dc[k];
                if(!in_bounds(nr, nc) || current_grid[nr][nc] == 0) {
                    adj_0 = true; 
                    break; 
                }
            }
            if(!adj_0) continue;
            
            // 2. Region must not vanish
            if(current_region_size[color] <= 1) continue;
            
            // 3. Buffer Check: Cannot expose a neighbor to 0 if it's not allowed
            bool buffer_ok = true;
            for(int k=0; k<4; ++k) {
                int nr = r + dr[k];
                int nc = c + dc[k];
                if(in_bounds(nr, nc)) {
                    int n_color = current_grid[nr][nc];
                    if(n_color != 0 && n_color != color && !is_adj_0[n_color]) {
                        buffer_ok = false; 
                        break;
                    }
                }
            }
            if(!buffer_ok) continue;
            
            // 4. Adjacency Preservation: Cannot break the last adjacency between color and any neighbor D
            bool edges_ok = true;
            int lost_neighbors[4];
            int ln_count = 0;
            
            for(int k=0; k<4; ++k) {
                int nr = r + dr[k];
                int nc = c + dc[k];
                if(in_bounds(nr, nc)) {
                    int n_color = current_grid[nr][nc];
                    if(n_color != 0 && n_color != color) {
                        lost_neighbors[ln_count++] = n_color;
                    }
                }
            }
            
            // Check if any neighbor connection would reach 0
            for(int k=0; k<ln_count; ++k) {
                int n_color = lost_neighbors[k];
                int count_occurrence = 0;
                for(int m=0; m<ln_count; ++m) if(lost_neighbors[m] == n_color) count_occurrence++;
                
                if(current_edge_counts[color][n_color] <= count_occurrence) {
                    edges_ok = false; break;
                }
            }
            if(!edges_ok) continue;
            
            // 5. Connectivity Check
            if(!check_connectivity(r, c, color)) continue;
            
            // All checks passed: Remove cell
            current_grid[r][c] = 0;
            current_region_size[color]--;
            changed = true;
            
            // Update edge counts
            for(int k=0; k<ln_count; ++k) {
                int n_color = lost_neighbors[k];
                // Only decrement once per edge; loop handles multi-edges correctly naturally
                // But we counted occurrences in the loop above? No, we iterate lost_neighbors array.
                // We should only decrement once per physical edge. 
                // Since lost_neighbors contains duplicates if multiple edges exist, iterating it is correct.
                current_edge_counts[color][n_color]--;
                current_edge_counts[n_color][color]--;
            }
        }
    }
    
    // Evaluate score (number of 0s)
    int score = 0;
    for(int i=0; i<N; ++i) 
        for(int j=0; j<N; ++j) 
            if(current_grid[i][j] == 0) score++;
            
    if(score > best_score) {
        best_score = score;
        memcpy(best_grid, current_grid, sizeof(current_grid));
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if(!(cin >> N >> M)) return 0;
    
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            cin >> initial_grid[i][j];
        }
    }

    // Precompute adjacency properties
    memset(is_adj_0, 0, sizeof(is_adj_0));
    memset(initial_edge_counts, 0, sizeof(initial_edge_counts));

    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            int u = initial_grid[i][j];
            // Check boundary
            if (i == 0 || i == N - 1 || j == 0 || j == N - 1) is_adj_0[u] = true;
            
            // Count horizontal edges
            if (j + 1 < N) {
                int v = initial_grid[i][j + 1];
                if (u != v) {
                    initial_edge_counts[u][v]++;
                    initial_edge_counts[v][u]++;
                }
            }
            // Count vertical edges
            if (i + 1 < N) {
                int v = initial_grid[i + 1][j];
                if (u != v) {
                    initial_edge_counts[u][v]++;
                    initial_edge_counts[v][u]++;
                }
            }
        }
    }

    // Initialize best solution with input
    memcpy(best_grid, initial_grid, sizeof(initial_grid));
    
    // Time management
    double start_time = (double)clock() / CLOCKS_PER_SEC;
    srand(12345); // Seed for reproducibility
    
    // Run solver repeatedly within time limit
    int iterations = 0;
    while(true) {
        solve();
        iterations++;
        double curr_time = (double)clock() / CLOCKS_PER_SEC;
        // Leave some margin for final I/O
        if(curr_time - start_time > 1.85) break; 
        if(iterations > 50) break; 
    }
    
    // Output best solution
    for(int i=0; i<N; ++i) {
        for(int j=0; j<N; ++j) {
            cout << best_grid[i][j] << (j==N-1 ? "" : " ");
        }
        cout << "\n";
    }
    
    return 0;
}