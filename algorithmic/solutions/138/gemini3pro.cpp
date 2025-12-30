#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <algorithm>
#include <cmath>
#include <queue>

using namespace std;

struct Preset {
    int id;
    int n, m;
    vector<string> grid;
};

struct Op {
    int type; // -4 to 0, or 1..k
    int x, y;
};

int N, M, K;
vector<string> current_grid;
vector<string> target_grid;
vector<Preset> presets;
vector<Op> operations;

// To track reserved status of cells
vector<vector<bool>> is_reserved;
map<char, int> target_counts;
map<char, int> reserved_counts;

void add_op(int type, int x, int y) {
    operations.push_back({type, x + 1, y + 1}); // 1-based output
}

void perform_swap(int r1, int c1, int r2, int c2) {
    if (r2 == r1 + 1 && c2 == c1) { // Down: -4 x y swaps (x,y) and (x+1,y)
        add_op(-4, r1, c1);
    } else if (r2 == r1 - 1 && c2 == c1) { // Up: -4 x-1 y swaps (x-1,y) and (x,y)
        add_op(-4, r2, c2);
    } else if (r2 == r1 && c2 == c1 - 1) { // Left: -2 x y swaps (x,y) and (x,y-1)
        add_op(-2, r1, c1);
    } else if (r2 == r1 && c2 == c1 + 1) { // Right: -2 x y+1 swaps (x,y+1) and (x,y)
        add_op(-2, r2, c2); 
    }

    swap(current_grid[r1][c1], current_grid[r2][c2]);
    bool temp = is_reserved[r1][c1];
    is_reserved[r1][c1] = is_reserved[r2][c2];
    is_reserved[r2][c2] = temp;
}

// BFS move to find path avoiding forbidden cells
// Moves the jelly at (r1, c1) to (r2, c2)
void move_jelly(int r1, int c1, int r2, int c2, const vector<vector<bool>>& forbidden) {
    if (r1 == r2 && c1 == c2) return;

    int cr = r1, cc = c1;
    while (cr != r2 || cc != c2) {
        queue<pair<int,int>> q;
        q.push({cr, cc});
        vector<vector<pair<int,int>>> parent(N, vector<pair<int,int>>(M, {-1, -1}));
        vector<vector<bool>> visited(N, vector<bool>(M, false));
        visited[cr][cc] = true;
        
        bool found = false;
        
        while(!q.empty()){
            auto [ur, uc] = q.front();
            q.pop();
            if (ur == r2 && uc == c2) {
                found = true;
                break;
            }
            
            int dr[] = {0, 0, 1, -1};
            int dc[] = {1, -1, 0, 0};
            for(int i=0; i<4; ++i){
                int nr = ur + dr[i];
                int nc = uc + dc[i];
                if(nr >= 0 && nr < N && nc >= 0 && nc < M && !visited[nr][nc]){
                    if(!forbidden[nr][nc] || (nr==r2 && nc==c2)){ 
                        visited[nr][nc] = true;
                        parent[nr][nc] = {ur, uc};
                        q.push({nr, nc});
                    }
                }
            }
        }
        
        if (!found) return;
        
        vector<pair<int,int>> path;
        int curr = r2, curc = c2;
        while(curr != cr || curc != cc){
            path.push_back({curr, curc});
            auto p = parent[curr][curc];
            curr = p.first;
            curc = p.second;
        }
        
        pair<int,int> next_step = path.back();
        perform_swap(cr, cc, next_step.first, next_step.second);
        cr = next_step.first;
        cc = next_step.second;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M >> K)) return 0;
    current_grid.resize(N);
    target_grid.resize(N);
    for (int i = 0; i < N; ++i) cin >> current_grid[i];
    for (int i = 0; i < N; ++i) cin >> target_grid[i];

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < M; ++j) {
            target_counts[target_grid[i][j]]++;
        }
    }

    presets.resize(K);
    for (int k = 0; k < K; ++k) {
        presets[k].id = k + 1;
        cin >> presets[k].n >> presets[k].m;
        presets[k].grid.resize(presets[k].n);
        for (int i = 0; i < presets[k].n; ++i) cin >> presets[k].grid[i];
    }

    is_reserved.assign(N, vector<bool>(M, false));
    int reserved_total = 0;

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < M; ++j) {
            char c = current_grid[i][j];
            if (reserved_counts[c] < target_counts[c]) {
                reserved_counts[c]++;
                is_reserved[i][j] = true;
                reserved_total++;
            }
        }
    }

    // Phase 1: Gather ingredients
    while (true) {
        bool complete = true;
        for (auto const& [key, val] : target_counts) {
            if (reserved_counts[key] < val) {
                complete = false;
                break;
            }
        }
        if (complete) break;

        int best_preset_idx = -1;
        int best_r = -1, best_c = -1;
        long long best_score = -1; 
        int garbage_count = N * M - reserved_total;

        for (int k = 0; k < K; ++k) {
            int area = presets[k].n * presets[k].m;
            if (area > garbage_count) continue;

            for (int r = 0; r <= N - presets[k].n; ++r) {
                for (int c = 0; c <= M - presets[k].m; ++c) {
                    int gain = 0;
                    map<char, int> temp_counts = reserved_counts;
                    for (int pr = 0; pr < presets[k].n; ++pr) {
                        for (int pc = 0; pc < presets[k].m; ++pc) {
                            char ch = presets[k].grid[pr][pc];
                            if (temp_counts[ch] < target_counts[ch]) {
                                gain++;
                                temp_counts[ch]++;
                            }
                        }
                    }

                    if (gain > 0) {
                        long long score = (long long)area * 100000 + gain; 
                        if (score > best_score) {
                            best_score = score;
                            best_preset_idx = k;
                            best_r = r;
                            best_c = c;
                        }
                    }
                }
            }
        }

        if (best_preset_idx == -1) {
            cout << -1 << endl;
            return 0;
        }

        Preset& p = presets[best_preset_idx];
        int r = best_r;
        int c = best_c;

        while(true) {
            pair<int,int> src = {-1, -1};
            for(int rr=r; rr<r+p.n; ++rr){
                for(int cc=c; cc<c+p.m; ++cc){
                    if(is_reserved[rr][cc]){
                        src = {rr, cc};
                        goto found_src;
                    }
                }
            }
            found_src:;
            if(src.first == -1) break;

            pair<int,int> dst = {-1, -1};
            queue<pair<int,int>> q;
            q.push(src);
            vector<vector<bool>> vis(N, vector<bool>(M, false));
            vis[src.first][src.second] = true;
            
            while(!q.empty()){
                auto [ur, uc] = q.front();
                q.pop();
                
                bool inside = (ur >= r && ur < r + p.n && uc >= c && uc < c + p.m);
                if(!inside && !is_reserved[ur][uc]){
                    dst = {ur, uc};
                    break;
                }
                
                int dr[] = {0,0,1,-1};
                int dc[] = {1,-1,0,0};
                for(int k=0; k<4; ++k){
                    int nr = ur+dr[k];
                    int nc = uc+dc[k];
                    if(nr>=0 && nr<N && nc>=0 && nc<M && !vis[nr][nc]){
                        vis[nr][nc] = true;
                        q.push({nr, nc});
                    }
                }
            }
            
            if(dst.first == -1) {
                cout << -1 << endl;
                return 0;
            }
            
            vector<vector<bool>> empty_forbidden(N, vector<bool>(M, false));
            move_jelly(src.first, src.second, dst.first, dst.second, empty_forbidden);
        }
        
        add_op(p.id, r, c);
        
        for(int i=0; i<p.n; ++i){
            for(int j=0; j<p.m; ++j){
                int grid_r = r + i;
                int grid_c = c + j;
                current_grid[grid_r][grid_c] = p.grid[i][j];
                is_reserved[grid_r][grid_c] = false;
            }
        }
        
        for(int i=0; i<N; ++i){
            for(int j=0; j<M; ++j){
                if (!is_reserved[i][j]) {
                    char ch = current_grid[i][j];
                    if (reserved_counts[ch] < target_counts[ch]) {
                        reserved_counts[ch]++;
                        reserved_total++;
                        is_reserved[i][j] = true;
                    }
                }
            }
        }
    }

    // Phase 2: Arrange
    vector<vector<bool>> locked(N, vector<bool>(M, false));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < M; ++j) {
            char target_char = target_grid[i][j];
            
            if (current_grid[i][j] == target_char) {
                 locked[i][j] = true;
                 continue;
            }
            
            pair<int,int> src = {-1, -1};
            queue<pair<int,int>> q;
            q.push({i, j});
            vector<vector<bool>> vis(N, vector<bool>(M, false));
            vis[i][j] = true;
            
            while(!q.empty()){
                auto [ur, uc] = q.front();
                q.pop();
                
                if(!locked[ur][uc] && current_grid[ur][uc] == target_char && (ur!=i || uc!=j)){
                     src = {ur, uc};
                     break;
                }
                
                int dr[] = {0,0,1,-1};
                int dc[] = {1,-1,0,0};
                for(int k=0; k<4; ++k){
                    int nr = ur+dr[k];
                    int nc = uc+dc[k];
                    if(nr>=0 && nr<N && nc>=0 && nc<M && !vis[nr][nc]){
                        if (!locked[nr][nc]) {
                             vis[nr][nc] = true;
                             q.push({nr, nc});
                        }
                    }
                }
            }
            
            if (src.first != -1) {
                move_jelly(src.first, src.second, i, j, locked);
                locked[i][j] = true;
            } else {
                cout << -1 << endl;
                return 0;
            }
        }
    }

    cout << operations.size() << "\n";
    for (const auto& op : operations) {
        cout << op.type << " " << op.x << " " << op.y << "\n";
    }

    return 0;
}