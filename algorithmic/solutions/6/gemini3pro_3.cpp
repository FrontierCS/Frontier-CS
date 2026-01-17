#include <iostream>
#include <vector>
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <algorithm>
#include <numeric>

using namespace std;

// Helper to get random double in [0, 1)
inline double rand_double() {
    return (double)rand() / (RAND_MAX + 1.0);
}

// Helper to get random int in [0, n-1]
inline int rand_int(int n) {
    return rand() % n;
}

// Function to create the map
std::vector<std::vector<int>> create_map(int N, int M, std::vector<int> A, std::vector<int> B) {
    // Determine bounds for K
    // We need K*K >= N to fit all colors
    int min_K_area = ceil(sqrt(N));
    
    // We need enough adjacencies.
    // Total adjacencies in KxK grid is 2K(K-1).
    // We need to support M edges.
    // This is a loose lower bound, but K must be at least this.
    int min_K_edges = 0;
    if (M > 0) {
        // Solving 2K^2 - 2K >= M for K. Approximation 2K^2 approx M
        min_K_edges = ceil(sqrt(M / 2.0));
    }
    
    int K = max(min_K_area, min_K_edges);
    if (K < 1) K = 1;
    
    // Adjacency matrix (1-based)
    // Using static array for speed given N <= 40
    static bool adj[45][45];
    for(int i=0; i<=N; ++i) 
        for(int j=0; j<=N; ++j) adj[i][j] = false;
        
    for(int i=0; i<M; ++i) {
        adj[A[i]][B[i]] = true;
        adj[B[i]][A[i]] = true;
    }
    
    // Clock for timeout per testcase
    clock_t start_time = clock();
    
    while (true) {
        int num_cells = K * K;
        
        // Initialize grid
        vector<vector<int>> grid(K, vector<int>(K));
        
        // Ensure all colors present
        vector<int> init_colors;
        init_colors.reserve(num_cells);
        for(int i=1; i<=N; ++i) init_colors.push_back(i);
        while(init_colors.size() < num_cells) init_colors.push_back(rand_int(N)+1);
        random_shuffle(init_colors.begin(), init_colors.end());
        
        for(int i=0; i<num_cells; ++i) {
            grid[i/K][i%K] = init_colors[i];
        }
        
        // Statistics
        // edge_counts[u][v] stores how many times colors u and v are adjacent
        static int edge_counts[45][45];
        for(int i=0; i<=N; ++i) 
            for(int j=0; j<=N; ++j) edge_counts[i][j] = 0;
            
        int invalid_adj = 0;
        int color_counts[45] = {0};
        
        // Initial computation of stats
        auto update_stats_full = [&]() {
            invalid_adj = 0;
            for(int i=1; i<=N; ++i) {
                for(int j=1; j<=N; ++j) edge_counts[i][j] = 0;
                color_counts[i] = 0;
            }
            
            for(int r=0; r<K; ++r) {
                for(int c=0; c<K; ++c) {
                    int u = grid[r][c];
                    color_counts[u]++;
                    // Check Right Neighbor
                    if (c+1 < K) {
                        int v = grid[r][c+1];
                        if (u != v) {
                            int mn = min(u, v), mx = max(u, v);
                            edge_counts[mn][mx]++;
                            if (!adj[mn][mx]) invalid_adj++;
                        }
                    }
                    // Check Down Neighbor
                    if (r+1 < K) {
                        int v = grid[r+1][c];
                        if (u != v) {
                            int mn = min(u, v), mx = max(u, v);
                            edge_counts[mn][mx]++;
                            if (!adj[mn][mx]) invalid_adj++;
                        }
                    }
                }
            }
        };
        
        update_stats_full();
        
        int missing_colors = 0;
        for(int i=1; i<=N; ++i) if(color_counts[i] == 0) missing_colors++;
        
        int missing_edges = 0;
        for(int i=0; i<M; ++i) {
            if(edge_counts[A[i]][B[i]] == 0) missing_edges++;
        }
        
        long long current_score = (long long)invalid_adj * 5000 + (long long)missing_colors * 5000 + (long long)missing_edges * 20;
        
        if (current_score == 0) return grid;
        
        // Simulated Annealing
        double T = 2.0;
        double min_T = 0.001;
        double cooling = 0.9999;
        int max_iters = 100000;
        if (K > 15) max_iters = 150000;
        if (K > 30) max_iters = 50000; 
        
        // Check time remaining
        double elapsed = (double)(clock() - start_time) / CLOCKS_PER_SEC;
        if (elapsed > 1.0) max_iters = 20000; 
        if (elapsed > 1.8) {
             // If time is running out, just return what we have? 
             // But we need a valid solution. We continue hoping to find one quickly or timeout.
        }

        for(int iter=0; iter<max_iters; ++iter) {
            int r = rand_int(K);
            int c = rand_int(K);
            int old_c = grid[r][c];
            int new_c = rand_int(N) + 1;
            
            if (old_c == new_c) continue;
            
            // Calculate delta
            int d_inv = 0;
            vector<pair<int, int>> decs, incs;
            decs.reserve(4); incs.reserve(4);
            
            int nr, nc;
            int dirs[4][2] = {{-1,0}, {1,0}, {0,-1}, {0,1}};
            
            for(int k=0; k<4; ++k) {
                nr = r + dirs[k][0];
                nc = c + dirs[k][1];
                if (nr >= 0 && nr < K && nc >= 0 && nc < K) {
                    int neighbor = grid[nr][nc];
                    if (neighbor != old_c) {
                        int mn = min(old_c, neighbor);
                        int mx = max(old_c, neighbor);
                        if (!adj[mn][mx]) d_inv--;
                        decs.push_back({mn, mx});
                    }
                    if (neighbor != new_c) {
                        int mn = min(new_c, neighbor);
                        int mx = max(new_c, neighbor);
                        if (!adj[mn][mx]) d_inv++;
                        incs.push_back({mn, mx});
                    }
                }
            }
            
            int d_col = 0;
            if (color_counts[old_c] == 1) d_col++;
            if (color_counts[new_c] == 0) d_col--;
            
            int d_miss_edge = 0;
            for(auto &p : decs) {
                if (edge_counts[p.first][p.second] == 1 && adj[p.first][p.second]) d_miss_edge++;
                edge_counts[p.first][p.second]--;
            }
            for(auto &p : incs) {
                if (edge_counts[p.first][p.second] == 0 && adj[p.first][p.second]) d_miss_edge--;
                edge_counts[p.first][p.second]++;
            }
            
            long long new_score = (long long)(invalid_adj + d_inv) * 5000 + 
                                  (long long)(missing_colors + d_col) * 5000 + 
                                  (long long)(missing_edges + d_miss_edge) * 20;
                                  
            bool accept = false;
            if (new_score <= current_score) accept = true;
            else {
                if (rand_double() < exp(-(new_score - current_score) / T)) accept = true;
            }
            
            if (accept) {
                grid[r][c] = new_c;
                invalid_adj += d_inv;
                missing_colors += d_col;
                missing_edges += d_miss_edge;
                color_counts[old_c]--;
                color_counts[new_c]++;
                current_score = new_score;
                if (current_score == 0) return grid;
            } else {
                // Revert changes to edge_counts
                for(auto &p : incs) edge_counts[p.first][p.second]--;
                for(auto &p : decs) edge_counts[p.first][p.second]++;
            }
            
            T *= cooling;
            if (T < min_T) T = min_T;
        }
        
        K++;
        if (K > 240) K = 240; 
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(42);
    int T;
    if (cin >> T) {
        while(T--) {
            int N, M;
            cin >> N >> M;
            vector<int> A(M), B(M);
            for(int i=0; i<M; ++i) {
                cin >> A[i] >> B[i];
            }
            vector<vector<int>> result = create_map(N, M, A, B);
            int P = result.size();
            cout << P << "\n";
            for(int i=0; i<P; ++i) {
                cout << result[i].size() << (i == P-1 ? "" : " ");
            }
            cout << "\n";
            for(int i=0; i<P; ++i) {
                for(int j=0; j<(int)result[i].size(); ++j) {
                    cout << result[i][j] << (j == result[i].size()-1 ? "" : " ");
                }
                cout << "\n";
            }
        }
    }
    return 0;
}