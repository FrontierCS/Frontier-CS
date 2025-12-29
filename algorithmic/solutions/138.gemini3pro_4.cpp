#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <algorithm>
#include <queue>
#include <cmath>

using namespace std;

struct Op {
    int type; // -4 to 0 for moves, 1..k for presets
    int x, y;
};

struct Preset {
    int id;
    int n, m;
    vector<string> grid;
};

int N, M, K;
vector<string> current_grid;
vector<string> target_grid;
vector<Preset> presets;
vector<Op> operations;
bool fixed_cells[25][25];

// Helper to check coords
bool in_bounds(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < M;
}

// Convert op code to relative coords for swap
// -4: (x, y) <-> (x+1, y)
// -3: (x, y) <-> (x-1, y)
// -2: (x, y) <-> (x, y-1)
// -1: (x, y) <-> (x, y+1)
// We output 1-based x, y.

void perform_swap(int r, int c, int dir) {
    int nr = r, nc = c;
    int code = 0;
    if (dir == 0) { nr = r + 1; code = -4; }
    else if (dir == 1) { nr = r - 1; code = -3; }
    else if (dir == 2) { nc = c - 1; code = -2; }
    else if (dir == 3) { nc = c + 1; code = -1; }
    
    // Output requires base position. 
    // -4 x y means swap (x,y) and (x+1,y). So base is r+1, c+1.
    // -3 x y means swap (x,y) and (x-1,y). So base is r+1, c+1.
    operations.push_back({code, r + 1, c + 1});
    swap(current_grid[r][c], current_grid[nr][nc]);
}

// Move char from (sr, sc) to (tr, tc) avoiding fixed cells
void move_piece(int sr, int sc, int tr, int tc) {
    if (sr == tr && sc == tc) return;
    
    // BFS to find path
    queue<pair<int, int>> q;
    q.push({sr, sc});
    vector<vector<pair<int, int>>> parent(N, vector<pair<int, int>>(M, {-1, -1}));
    vector<vector<bool>> visited(N, vector<bool>(M, false));
    visited[sr][sc] = true;
    
    bool found = false;
    while(!q.empty()){
        pair<int, int> curr = q.front(); q.pop();
        if(curr.first == tr && curr.second == tc){
            found = true;
            break;
        }
        int dr[] = {1, -1, 0, 0};
        int dc[] = {0, 0, -1, 1};
        for(int i=0; i<4; ++i){
            int nr = curr.first + dr[i];
            int nc = curr.second + dc[i];
            if(in_bounds(nr, nc) && !visited[nr][nc] && !fixed_cells[nr][nc]){
                visited[nr][nc] = true;
                parent[nr][nc] = curr;
                q.push({nr, nc});
            }
        }
    }
    
    if (!found) return;
    
    // Reconstruct path
    vector<pair<int, int>> path;
    int cr = tr, cc = tc;
    while(cr != sr || cc != sc){
        path.push_back({cr, cc});
        pair<int, int> p = parent[cr][cc];
        cr = p.first;
        cc = p.second;
    }
    path.push_back({sr, sc});
    reverse(path.begin(), path.end());
    
    // Execute swaps
    for(size_t i=0; i<path.size()-1; ++i){
        int r1 = path[i].first;
        int c1 = path[i].second;
        int r2 = path[i+1].first;
        int c2 = path[i+1].second;
        
        int dir = -1;
        if(r2 == r1 + 1) dir = 0; // down
        else if(r2 == r1 - 1) dir = 1; // up
        else if(c2 == c1 - 1) dir = 2; // left
        else if(c2 == c1 + 1) dir = 3; // right
        
        perform_swap(r1, c1, dir);
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N >> M >> K)) return 0;
    
    current_grid.resize(N);
    for(int i=0; i<N; ++i) cin >> current_grid[i];
    
    target_grid.resize(N);
    for(int i=0; i<N; ++i) cin >> target_grid[i];
    
    for(int i=0; i<K; ++i){
        Preset p;
        p.id = i + 1;
        cin >> p.n >> p.m;
        p.grid.resize(p.n);
        for(int r=0; r<p.n; ++r) cin >> p.grid[r];
        presets.push_back(p);
    }
    
    map<char, int> target_counts;
    for(const string& s : target_grid) for(char c : s) target_counts[c]++;
    
    int presets_used = 0;
    
    while(presets_used < 400) {
        map<char, int> current_counts;
        for(const string& s : current_grid) for(char c : s) current_counts[c]++;
        
        map<char, int> missing;
        map<char, int> excess;
        int missing_total = 0;
        int excess_total = 0;
        
        for(auto const& [key, val] : target_counts) {
            int cur = current_counts[key];
            if(val > cur) {
                missing[key] = val - cur;
                missing_total += val - cur;
            }
        }
        for(auto const& [key, val] : current_counts) {
            int tgt = target_counts[key];
            if(val > tgt) {
                excess[key] = val - tgt;
                excess_total += val - tgt;
            }
        }
        
        if(missing_total == 0) break;
        
        int best_score = -1e9;
        int best_p_idx = -1;
        int best_r = -1, best_c = -1;
        
        for(int i=0; i<K; ++i){
            const Preset& p = presets[i];
            int size = p.n * p.m;
            int gain = 0;
            map<char, int> temp_missing = missing;
            for(const string& s : p.grid) for(char c : s) {
                if(temp_missing.count(c) && temp_missing[c] > 0) {
                    gain++;
                    temp_missing[c]--;
                }
            }
            
            int cost = max(0, size - excess_total);
            int score = gain - cost;
            
            if(score > best_score) {
                best_score = score;
                best_p_idx = i;
                if (p.n <= N && p.m <= M) {
                    best_r = 0; best_c = 0;
                } else {
                    best_r = -1;
                }
            }
        }
        
        if (best_score <= 0) {
            cout << "-1" << endl;
            return 0;
        }
        
        const Preset& p = presets[best_p_idx];
        int pr = best_r;
        int pc = best_c;
        int size = p.n * p.m;
        
        vector<pair<int, int>> victims;
        vector<pair<int, int>> others;
        
        for(int r=0; r<N; ++r) for(int c=0; c<M; ++c) {
            char ch = current_grid[r][c];
            if(excess[ch] > 0) {
                victims.push_back({r, c});
                excess[ch]--;
            } else {
                others.push_back({r, c});
            }
        }
        
        while(victims.size() < size) {
            victims.push_back(others.back());
            others.pop_back();
        }
        if (victims.size() > size) {
            victims.resize(size);
        }
        
        vector<vector<bool>> in_preset(N, vector<bool>(M, false));
        for(int r=0; r<p.n; ++r) for(int c=0; c<p.m; ++c) in_preset[pr+r][pc+c] = true;
        
        vector<pair<int, int>> victims_outside;
        vector<pair<int, int>> non_victims_inside;
        
        vector<vector<bool>> is_victim_pos(N, vector<bool>(M, false));
        for(auto v : victims) is_victim_pos[v.first][v.second] = true;
        
        for(int r=0; r<p.n; ++r) {
            for(int c=0; c<p.m; ++c) {
                int gr = pr + r;
                int gc = pc + c;
                if (!is_victim_pos[gr][gc]) {
                    non_victims_inside.push_back({gr, gc});
                }
            }
        }
        
        for(auto v : victims) {
            if (!in_preset[v.first][v.second]) {
                victims_outside.push_back(v);
            }
        }
        
        while(!non_victims_inside.empty()) {
            pair<int, int> inside = non_victims_inside.back(); non_victims_inside.pop_back();
            pair<int, int> outside = victims_outside.back(); victims_outside.pop_back();
            move_piece(outside.first, outside.second, inside.first, inside.second);
        }
        
        operations.push_back({p.id, pr + 1, pc + 1});
        for(int r=0; r<p.n; ++r) for(int c=0; c<p.m; ++c) {
            current_grid[pr+r][pc+c] = p.grid[r][c];
        }
        presets_used++;
    }
    
    map<char, int> counts;
    for(const string& s : current_grid) for(char c : s) counts[c]++;
    for(auto const& [key, val] : target_counts) {
        if(counts[key] < val) {
             cout << "-1" << endl;
             return 0;
        }
    }
    
    for(int r = N - 1; r >= 0; --r) {
        for(int c = M - 1; c >= 0; --c) {
            char tgt = target_grid[r][c];
            if(current_grid[r][c] == tgt) {
                fixed_cells[r][c] = true;
                continue;
            }
            
            queue<pair<int, int>> q;
            q.push({r, c});
            vector<vector<bool>> vis(N, vector<bool>(M, false));
            vis[r][c] = true;
            pair<int, int> source = {-1, -1};
            
            while(!q.empty()){
                pair<int, int> curr = q.front(); q.pop();
                if(current_grid[curr.first][curr.second] == tgt && !fixed_cells[curr.first][curr.second]){
                    source = curr;
                    break;
                }
                int dr[] = {1, -1, 0, 0};
                int dc[] = {0, 0, -1, 1};
                for(int k=0; k<4; ++k){
                    int nr = curr.first + dr[k];
                    int nc = curr.second + dc[k];
                    if(in_bounds(nr, nc) && !vis[nr][nc] && !fixed_cells[nr][nc]){
                        vis[nr][nc] = true;
                        q.push({nr, nc});
                    }
                }
            }
            
            if(source.first == -1) {
                cout << "-1" << endl;
                return 0;
            }
            
            move_piece(source.first, source.second, r, c);
            fixed_cells[r][c] = true;
        }
    }
    
    cout << operations.size() << endl;
    for(const auto& op : operations) {
        cout << op.type << " " << op.x << " " << op.y << "\n";
    }
    
    return 0;
}