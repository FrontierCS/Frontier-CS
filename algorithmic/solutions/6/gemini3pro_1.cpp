#include <vector>
#include <cmath>
#include <algorithm>
#include <cstdlib>
#include <ctime>
#include <iostream>
#include <map>

using namespace std;

// Global variables for convenience within create_map
static bool adj[45][45];
static int color_counts[45];
static int grid[245][245];
static int edge_realized_counts[45][45];
static int N_val, M_val;

// Helper to check if placing a color at (r, c) is valid according to problem conditions
// Condition: For each pair of adjacent cells with different colors, the countries must be adjacent.
bool is_valid(int r, int c, int color, int K) {
    int dr[] = {-1, 1, 0, 0};
    int dc[] = {0, 0, -1, 1};
    for (int i = 0; i < 4; i++) {
        int nr = r + dr[i];
        int nc = c + dc[i];
        if (nr >= 0 && nr < K && nc >= 0 && nc < K) {
            int neighbor_color = grid[nr][nc];
            // 0 is treated as empty, which will be filled later.
            // A non-empty neighbor must be either same color or adjacent in graph.
            if (neighbor_color != 0 && neighbor_color != color) {
                if (!adj[color][neighbor_color]) return false;
            }
        }
    }
    return true;
}

// Recursive function to embed a spanning tree into the grid
bool embed_tree(int u, int r, int c, int K, const vector<vector<int>>& tree_adj, vector<bool>& visited) {
    visited[u] = true;
    grid[r][c] = u;
    color_counts[u]++;
    
    // Randomize processing order of neighbors to produce different layouts
    vector<int> neighbors = tree_adj[u];
    for (int i = 0; i < neighbors.size(); i++) swap(neighbors[i], neighbors[rand() % neighbors.size()]);
    
    for (int v : neighbors) {
        if (!visited[v]) {
            int dr[] = {-1, 1, 0, 0};
            int dc[] = {0, 0, -1, 1};
            vector<int> dirs = {0, 1, 2, 3};
            for (int i = 0; i < 4; i++) swap(dirs[i], dirs[rand() % 4]);
            
            bool placed = false;
            for (int i : dirs) {
                int nr = r + dr[i];
                int nc = c + dc[i];
                if (nr >= 0 && nr < K && nc >= 0 && nc < K && grid[nr][nc] == 0) {
                    if (is_valid(nr, nc, v, K)) {
                        if (embed_tree(v, nr, nc, K, tree_adj, visited)) {
                            placed = true;
                        }
                    }
                }
            }
            if (!placed) return false; 
        }
    }
    return true;
}

vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    N_val = N;
    M_val = M;
    
    // Reset adjacency matrix
    for (int i = 1; i <= N; i++) {
        for (int j = 1; j <= N; j++) adj[i][j] = false;
    }
    for (int i = 0; i < M; i++) {
        adj[A[i]][B[i]] = true;
        adj[B[i]][A[i]] = true;
    }
    
    // Build spanning forest to ensure initial connectivity and presence of all nodes
    vector<vector<int>> tree_adj(N + 1);
    {
        vector<bool> vis(N + 1, false);
        for(int start_node = 1; start_node <= N; ++start_node) {
            if(vis[start_node]) continue;
            vis[start_node] = true;
            vector<int> bfs_q; 
            bfs_q.push_back(start_node);
            int h = 0;
            while(h < bfs_q.size()){
                int u = bfs_q[h++];
                vector<int> nb;
                for(int v=1; v<=N; ++v) if(adj[u][v]) nb.push_back(v);
                for(int k=0; k<nb.size(); ++k) swap(nb[k], nb[rand()%nb.size()]);
                for(int v : nb){
                    if(!vis[v]){
                        vis[v] = true;
                        tree_adj[u].push_back(v);
                        tree_adj[v].push_back(u);
                        bfs_q.push_back(v);
                    }
                }
            }
        }
    }
    
    // Iteratively try to find a solution for K, starting from a small heuristic value
    int start_K = (int)ceil(sqrt(N));
    if (start_K < 2 && N > 1) start_K = 2;
    if (N == 1) start_K = 1;

    for (int K = start_K; K <= 240; K++) {
        // Number of attempts for current K. 
        int restarts = (K <= N + 2) ? 10 : 2; 
        if (K > N + 5) restarts = 1; 
        
        for (int rst = 0; rst < restarts; rst++) {
            // Clear grid and counters
            for(int i=0; i<K; ++i) for(int j=0; j<K; ++j) grid[i][j] = 0;
            for(int i=1; i<=N; ++i) color_counts[i] = 0;
            for(int i=1; i<=N; ++i) for(int j=1; j<=N; ++j) edge_realized_counts[i][j] = 0;
            
            // Embed the spanning forest
            vector<bool> visited(N + 1, false);
            bool fail = false;
            for(int i=1; i<=N; ++i) {
                if(!visited[i]) {
                    int r = -1, c = -1;
                    // Try to place new component
                    if(i == 1 && grid[K/2][K/2] == 0) { r=K/2; c=K/2; }
                    else {
                        // Find a random free spot
                        int tries = 0;
                        while(tries < 50) {
                            int tr = rand()%K; int tc = rand()%K;
                            if(grid[tr][tc] == 0) { r=tr; c=tc; break; }
                            tries++;
                        }
                        // If random fail, linear scan
                        if(r == -1) {
                             for(int rr=0; rr<K; ++rr){
                                for(int cc=0; cc<K; ++cc){
                                    if(grid[rr][cc] == 0) { r=rr; c=cc; goto found; }
                                }
                            }
                            found:;
                        }
                    }
                    if(r == -1) { fail = true; break; }
                    
                    if(!embed_tree(i, r, c, K, tree_adj, visited)) {
                        fail = true; break;
                    }
                }
            }
            if(fail) continue;
            
            // Initialize stats based on the embedding
            int current_realized = 0;
            int empty_cells = 0;
            for(int i=0; i<K; ++i){
                for(int j=0; j<K; ++j){
                    if(grid[i][j] == 0) { empty_cells++; continue; }
                    int u = grid[i][j];
                    // Check neighbors to count edges
                    int dr[] = {0, 1};
                    int dc[] = {1, 0};
                    for(int d=0; d<2; ++d) {
                        int ni = i + dr[d];
                        int nj = j + dc[d];
                        if (ni < K && nj < K && grid[ni][nj] != 0) {
                            int v = grid[ni][nj];
                            if(u != v){
                                if(edge_realized_counts[u][v] == 0 && adj[u][v]) current_realized++;
                                edge_realized_counts[u][v]++;
                                edge_realized_counts[v][u]++;
                            }
                        }
                    }
                }
            }
            
            // Simulated Annealing / Random Search
            int max_iter = 15000;
            if (K < N) max_iter = 30000;
            
            for(int iter=0; iter<max_iter; ++iter){
                if(empty_cells == 0 && current_realized == M) break;
                
                int r = rand() % K;
                int c = rand() % K;
                int old_c = grid[r][c];
                
                // Prioritize filling empty cells
                if(empty_cells > 0 && old_c != 0 && rand()%100 < 70) continue; 
                if(empty_cells > 0 && old_c == 0) {
                     // Find an empty cell if we picked a filled one by luck? 
                     // Or just rely on random picking eventually hitting an empty one.
                     // To speed up, try to pick empty explicitly sometimes
                     int tries = 0;
                     while(grid[r][c] != 0 && tries < 5) {
                         r = rand() % K; c = rand() % K;
                         tries++;
                     }
                     if(grid[r][c] != 0) continue;
                     old_c = 0;
                }
                
                int new_c = (rand() % N) + 1;
                if(new_c == old_c) continue;
                // Cannot remove last instance of a color
                if(old_c != 0 && color_counts[old_c] == 1) continue;
                
                if(!is_valid(r, c, new_c, K)) continue;
                
                // Calculate gain
                int realized_gain = 0;
                int dr[] = {-1, 1, 0, 0};
                int dc[] = {0, 0, -1, 1};
                
                // Impact of removing old
                if(old_c != 0){
                    for(int d=0; d<4; ++d){
                        int nr = r+dr[d]; int nc = c+dc[d];
                        if(nr>=0 && nr<K && nc>=0 && nc<K){
                            int nb = grid[nr][nc];
                            if(nb!=0 && nb!=old_c){
                                if(edge_realized_counts[old_c][nb] == 1 && adj[old_c][nb]) realized_gain--;
                            }
                        }
                    }
                }
                
                // Impact of adding new
                for(int d=0; d<4; ++d){
                    int nr = r+dr[d]; int nc = c+dc[d];
                    if(nr>=0 && nr<K && nc>=0 && nc<K){
                        int nb = grid[nr][nc];
                        if(nb!=0 && nb!=new_c){
                            if(edge_realized_counts[new_c][nb] == 0 && adj[new_c][nb]) realized_gain++;
                        }
                    }
                }
                
                // Acceptance probability
                bool accept = false;
                if(old_c == 0) accept = true; // Always fill empty cells
                else {
                    if(realized_gain > 0) accept = true;
                    else if(realized_gain == 0 && rand()%20==0) accept = true;
                    else if(realized_gain < 0 && rand()%1000==0) accept = true;
                }
                
                if(accept){
                    if(old_c != 0){
                        color_counts[old_c]--;
                        for(int d=0; d<4; ++d){
                            int nr = r+dr[d]; int nc = c+dc[d];
                            if(nr>=0 && nr<K && nc>=0 && nc<K){
                                int nb = grid[nr][nc];
                                if(nb!=0 && nb!=old_c){
                                    if(edge_realized_counts[old_c][nb] == 1 && adj[old_c][nb]) current_realized--;
                                    edge_realized_counts[old_c][nb]--;
                                    edge_realized_counts[nb][old_c]--;
                                }
                            }
                        }
                    } else {
                        empty_cells--;
                    }
                    
                    grid[r][c] = new_c;
                    color_counts[new_c]++;
                    
                    for(int d=0; d<4; ++d){
                        int nr = r+dr[d]; int nc = c+dc[d];
                        if(nr>=0 && nr<K && nc>=0 && nc<K){
                            int nb = grid[nr][nc];
                            if(nb!=0 && nb!=new_c){
                                if(edge_realized_counts[new_c][nb] == 0 && adj[new_c][nb]) current_realized++;
                                edge_realized_counts[new_c][nb]++;
                                edge_realized_counts[nb][new_c]++;
                            }
                        }
                    }
                }
            }
            
            if(empty_cells == 0 && current_realized == M){
                vector<vector<int>> res(K, vector<int>(K));
                for(int i=0; i<K; ++i) for(int j=0; j<K; ++j) res[i][j] = grid[i][j];
                return res;
            }
        }
    }
    return {};
}

int main() {
    srand(time(NULL));
    int T;
    if (cin >> T) {
        while(T--) {
            int N, M;
            if (!(cin >> N >> M)) break;
            vector<int> A(M), B(M);
            for(int i=0; i<M; ++i) cin >> A[i] >> B[i];
            
            vector<vector<int>> result = create_map(N, M, A, B);
            
            cout << result.size() << endl;
            for(int i=0; i<result.size(); ++i) {
                cout << result[i].size();
                for(int j=0; j<result[i].size(); ++j) {
                    cout << " " << result[i][j];
                }
                cout << endl;
            }
        }
    }
    return 0;
}