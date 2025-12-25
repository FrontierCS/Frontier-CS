#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <queue>
#include <cmath>
#include <ctime>
#include <cstring>
#include <cassert>
#include <random>

using namespace std;

// Global Constants
int N;
int T_max;
int start_grid[15][15];
int target_grid[15][15];
string solution = "";

// Directions: L, U, R, D
int dr[4] = {0, -1, 0, 1};
int dc[4] = {-1, 0, 1, 0};
char dirs[4] = {'L', 'U', 'R', 'D'};

// Helper Functions
int hex_to_int(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    return c - 'a' + 10;
}

bool has_conn(int val, int d) {
    return (val >> d) & 1;
}

bool are_connected(int v1, int v2, int d12) {
    int d21 = d12 ^ 2; 
    return has_conn(v1, d12) && has_conn(v2, d21);
}

// Disjoint Set Union
struct DSU {
    vector<int> parent;
    vector<int> sz;
    DSU(int n) {
        parent.resize(n);
        sz.assign(n, 1);
        for(int i=0; i<n; i++) parent[i] = i;
    }
    int find(int i) {
        if (parent[i] == i) return i;
        return parent[i] = find(parent[i]);
    }
    void unite(int i, int j) {
        int root_i = find(i);
        int root_j = find(j);
        if (root_i != root_j) {
            if (sz[root_i] < sz[root_j]) swap(root_i, root_j);
            parent[root_j] = root_i;
            sz[root_i] += sz[root_j];
        }
    }
};

int calc_score(const vector<int>& grid_flat) {
    DSU dsu(N*N);
    int edges = 0;
    for (int r = 0; r < N; r++) {
        for (int c = 0; c < N; c++) {
            int idx = r*N + c;
            int val = grid_flat[idx];
            if (val == 0) continue;
            
            // Right
            if (c + 1 < N) {
                int n_idx = r*N + c + 1;
                int n_val = grid_flat[n_idx];
                if (n_val != 0 && are_connected(val, n_val, 2)) {
                    dsu.unite(idx, n_idx);
                    edges++;
                }
            }
            // Down
            if (r + 1 < N) {
                int n_idx = (r+1)*N + c;
                int n_val = grid_flat[n_idx];
                if (n_val != 0 && are_connected(val, n_val, 3)) {
                    dsu.unite(idx, n_idx);
                    edges++;
                }
            }
        }
    }
    
    int max_sz = 0;
    for (int i = 0; i < N*N; i++) {
        if (grid_flat[i] != 0 && dsu.parent[i] == i) {
            max_sz = max(max_sz, dsu.sz[i]);
        }
    }
    return max_sz * 1000 + edges; 
}

// Solver State
struct Point { int r, c; };
Point current_pos[100]; 
int tile_at[15][15];   
bool locked[15][15];
int empty_r, empty_c;

void apply_move(int dir) {
    int nr = empty_r + dr[dir];
    int nc = empty_c + dc[dir];
    int id = tile_at[nr][nc];
    tile_at[empty_r][empty_c] = id;
    tile_at[nr][nc] = -1;
    current_pos[id] = {empty_r, empty_c};
    empty_r = nr;
    empty_c = nc;
    solution += dirs[dir];
}

bool bfs_move_empty(int tr, int tc) {
    if (empty_r == tr && empty_c == tc) return true;
    queue<pair<int,int>> q;
    q.push({empty_r, empty_c});
    int visited[15][15];
    int parent_dir[15][15];
    memset(visited, 0, sizeof(visited));
    visited[empty_r][empty_c] = 1;
    
    bool found = false;
    while(!q.empty()){
        auto [r, c] = q.front(); q.pop();
        if(r == tr && c == tc) { found = true; break; }
        for(int i=0; i<4; i++){
            int nr = r + dr[i];
            int nc = c + dc[i];
            if(nr>=0 && nr<N && nc>=0 && nc<N && !visited[nr][nc] && !locked[nr][nc]){
                visited[nr][nc] = 1;
                parent_dir[nr][nc] = i;
                q.push({nr, nc});
            }
        }
    }
    
    if(!found) return false;
    
    vector<int> path;
    int curr_r = tr, curr_c = tc;
    while(curr_r != empty_r || curr_c != empty_c){
        int d = parent_dir[curr_r][curr_c];
        path.push_back(d);
        curr_r -= dr[d];
        curr_c -= dc[d];
    }
    reverse(path.begin(), path.end());
    for(int d : path) apply_move(d);
    return true;
}

void bring_tile(int id, int tr, int tc) {
    while(current_pos[id].r != tr || current_pos[id].c != tc) {
        int cr = current_pos[id].r;
        int cc = current_pos[id].c;
        queue<pair<int,int>> q;
        q.push({cr, cc});
        int dist[15][15];
        int p_move[15][15];
        memset(dist, -1, sizeof(dist));
        dist[cr][cc] = 0;
        
        bool found = false;
        while(!q.empty()){
            auto [r, c] = q.front(); q.pop();
            if(r == tr && c == tc) { found = true; break; }
            for(int i=0; i<4; i++){
                int nr = r + dr[i];
                int nc = c + dc[i];
                if(nr>=0 && nr<N && nc>=0 && nc<N && dist[nr][nc]==-1 && !locked[nr][nc]){
                    dist[nr][nc] = dist[r][c] + 1;
                    p_move[nr][nc] = i;
                    q.push({nr, nc});
                }
            }
        }
        
        int next_r = tr, next_c = tc;
        while(dist[next_r][next_c] > 1){
            int d = p_move[next_r][next_c];
            next_r -= dr[d];
            next_c -= dc[d];
        }
        
        locked[cr][cc] = true;
        bfs_move_empty(next_r, next_c);
        locked[cr][cc] = false;
        
        for(int i=0; i<4; i++){
            if(next_r + dr[i] == cr && next_c + dc[i] == cc) {
                apply_move(i);
                break;
            }
        }
    }
    locked[tr][tc] = true;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    clock_t start_time = clock();

    cin >> N >> T_max;
    vector<int> tiles;
    int initial_empty_pos = -1;
    for (int i = 0; i < N; i++) {
        string s; cin >> s;
        for (int j = 0; j < N; j++) {
            start_grid[i][j] = hex_to_int(s[j]);
            tiles.push_back(start_grid[i][j]);
            if(start_grid[i][j] == 0) initial_empty_pos = i*N+j;
        }
    }

    // SA to find target configuration
    vector<int> best_grid = tiles;
    // Ensure 0 is at N-1, N-1
    for(int i=0; i<N*N; i++) if(best_grid[i] == 0) {
        swap(best_grid[i], best_grid[N*N-1]);
        break;
    }
    
    int best_sc = calc_score(best_grid);
    vector<int> cur_grid = best_grid;
    
    mt19937 rng(12345);
    
    while((double)(clock() - start_time) / CLOCKS_PER_SEC < 1.7) {
        int idx1 = rng() % (N*N - 1); // Exclude last (empty)
        int idx2 = rng() % (N*N - 1);
        if(idx1 == idx2) continue;
        
        swap(cur_grid[idx1], cur_grid[idx2]);
        int sc = calc_score(cur_grid);
        if(sc >= best_sc) {
            best_sc = sc;
            best_grid = cur_grid;
        } else {
            // Revert
            swap(cur_grid[idx1], cur_grid[idx2]);
        }
    }
    
    // Build Target Assignment
    for(int i=0; i<N; i++)
        for(int j=0; j<N; j++)
            target_grid[i][j] = best_grid[i*N+j];
            
    // Assign IDs and fix parity
    // ID mapping: physical tiles from start_grid -> target positions
    vector<int> start_ids(N*N);
    vector<vector<int>> available_pos(16);
    for(int i=0; i<N*N; i++) {
        if(start_grid[i/N][i%N] == 0) {
            start_ids[i] = -1; 
        } else {
            start_ids[i] = i; // Use initial pos as ID
        }
    }
    
    vector<int> target_assignment(N*N); // target pos -> ID
    // Count available
    vector<vector<int>> val_to_ids(16);
    for(int i=0; i<N*N; i++) {
        if(start_ids[i] != -1)
            val_to_ids[start_grid[i/N][i%N]].push_back(i);
    }
    
    // Assign greedily (arbitrary)
    for(int i=0; i<N*N; i++) {
        if(target_grid[i/N][i%N] == 0) {
            target_assignment[i] = -1;
        } else {
            int val = target_grid[i/N][i%N];
            target_assignment[i] = val_to_ids[val].back();
            val_to_ids[val].pop_back();
        }
    }
    
    // Check Parity
    // Flatten target assignment excluding empty
    vector<int> p;
    for(int i=0; i<N*N; i++) if(target_assignment[i] != -1) p.push_back(target_assignment[i]);
    
    int inversions = 0;
    for(size_t i=0; i<p.size(); i++)
        for(size_t j=i+1; j<p.size(); j++)
            if(p[i] > p[j]) inversions++;
            
    // Empty distance
    // Start empty pos
    int er = initial_empty_pos / N;
    int ec = initial_empty_pos % N;
    // Target empty pos (N-1, N-1)
    int tr = N-1, tc = N-1;
    int dist = abs(er - tr) + abs(ec - tc);
    
    if ((inversions + dist) % 2 != 0) {
        // Fix parity: swap two identical tiles in target
        bool fixed = false;
        for(int v=1; v<16; v++) { // ignore 0
            vector<int> pos_indices;
            for(int i=0; i<N*N; i++) {
                if(target_grid[i/N][i%N] == v) pos_indices.push_back(i);
            }
            if(pos_indices.size() >= 2) {
                swap(target_assignment[pos_indices[0]], target_assignment[pos_indices[1]]);
                fixed = true;
                break;
            }
        }
        if(!fixed) {
             // Swap first two non-empty if no duplicates (rare)
             int p1=-1, p2=-1;
             for(int i=0; i<N*N; i++) {
                 if(target_assignment[i] != -1) {
                     if(p1 == -1) p1 = i;
                     else { p2 = i; break; }
                 }
             }
             if(p1 != -1 && p2 != -1) swap(target_assignment[p1], target_assignment[p2]);
        }
    }
    
    // Initialize solver state
    for(int i=0; i<N*N; i++) {
        if(target_assignment[i] != -1) {
            int id = target_assignment[i]; // id is initial pos
            current_pos[id] = {id/N, id%N};
            tile_at[id/N][id%N] = id;
        }
    }
    empty_r = initial_empty_pos / N;
    empty_c = initial_empty_pos % N;
    tile_at[empty_r][empty_c] = -1;
    
    memset(locked, 0, sizeof(locked));
    
    // Phase 2: Solve
    int target_to_id[15][15];
    for(int i=0; i<N*N; i++) target_to_id[i/N][i%N] = target_assignment[i];

    for(int r=0; r<N-2; r++) {
        for(int c=0; c<N; c++) {
            if(c < N-2) {
                bring_tile(target_to_id[r][c], r, c);
            } else if (c == N-2) {
                int id = target_to_id[r][c];
                int id_next = target_to_id[r][c+1];
                bring_tile(id, r+1, c);
                locked[r+1][c] = true;
                bring_tile(id_next, r, c);
                locked[r][c] = true;
                
                locked[r+1][c] = false;
                locked[r][c] = false;
                
                locked[r+1][c] = true; 
                locked[r][c] = true; 
                bfs_move_empty(r, c+1);
                locked[r+1][c] = false;
                locked[r][c] = false;
                
                apply_move(0); 
                apply_move(3);
                locked[r][c] = true;
                locked[r][c+1] = true;
            }
        }
    }
    
    for(int c=0; c<N-2; c++) {
        int r = N-2;
        int id = target_to_id[r][c];
        int id_next = target_to_id[r+1][c];
        
        bring_tile(id, r, c+1);
        locked[r][c+1] = true;
        bring_tile(id_next, r, c);
        locked[r][c] = true;
        
        locked[r][c+1] = false;
        locked[r][c] = false;
        
        locked[r][c+1] = true;
        locked[r][c] = true;
        bfs_move_empty(r+1, c);
        locked[r][c+1] = false;
        locked[r][c] = false;
        
        apply_move(1);
        apply_move(2);
        
        locked[r][c] = true;
        locked[r+1][c] = true;
    }
    
    // Last 2x2
    for(int r=N-2; r<N; r++) for(int c=N-2; c<N; c++) locked[r][c] = false;
    
    vector<int> desired_ids;
    desired_ids.push_back(target_to_id[N-2][N-2]);
    desired_ids.push_back(target_to_id[N-2][N-1]);
    desired_ids.push_back(target_to_id[N-1][N-2]);
    desired_ids.push_back(-1);
    
    int rr[] = {N-2, N-2, N-1, N-1};
    int cc[] = {N-2, N-1, N-2, N-1};
    
    map<vector<int>, string> visited_states;
    queue<vector<int>> q;
    vector<int> initial_state(4);
    for(int i=0; i<4; i++) initial_state[i] = tile_at[rr[i]][cc[i]];
    visited_states[initial_state] = "";
    q.push(initial_state);
    
    while(!q.empty()){
        vector<int> curr = q.front(); q.pop();
        if (curr == desired_ids) {
            string moves = visited_states[curr];
            for(char c : moves) {
                int d = -1;
                if(c=='L') d=0; if(c=='U') d=1; if(c=='R') d=2; if(c=='D') d=3;
                apply_move(d);
            }
            break;
        }
        string path = visited_states[curr];
        if(path.length() > 22) continue; 
        
        int z = -1;
        for(int i=0; i<4; i++) if(curr[i] == -1) z = i;
        int zr = rr[z], zc = cc[z];
        
        for(int k=0; k<4; k++){
            int nr = zr + dr[k];
            int nc = zc + dc[k];
            if(nr >= N-2 && nr < N && nc >= N-2 && nc < N) {
                int nz = -1;
                for(int j=0; j<4; j++) if(rr[j]==nr && cc[j]==nc) nz = j;
                vector<int> next_s = curr;
                swap(next_s[z], next_s[nz]);
                if(visited_states.find(next_s) == visited_states.end()){
                    visited_states[next_s] = path + dirs[k];
                    q.push(next_s);
                }
            }
        }
    }
    
    cout << solution << endl;
    return 0;
}