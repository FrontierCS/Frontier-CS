#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <map>
#include <set>

using namespace std;

struct Preset {
    int h, w;
    vector<string> mat;
    int id;
};

int N, M, K;
vector<string> grid;
vector<string> target;
vector<Preset> presets;

struct Op {
    int type; // -4 to 0, or 1..K
    int x, y;
};
vector<Op> operations;

void add_op(int type, int x, int y) {
    operations.push_back({type, x, y});
}

// Coordinate conversion: internal 0-based, output 1-based
// -4 x y: swaps (x,y) and (x+1,y). x < n
// -3 x y: swaps (x,y) and (x-1,y). x > 1
// -2 x y: swaps (x,y) and (x,y-1). y > 1
// -1 x y: swaps (x,y) and (x,y+1). y < m
// 0 x y: rotate 2x2 at x,y
// k x y: preset at x,y

void perform_swap(int r1, int c1, int r2, int c2) {
    int type = -100;
    if (r2 == r1 + 1 && c2 == c1) type = -4; // down
    else if (r2 == r1 - 1 && c2 == c1) type = -3; // up
    else if (r2 == r1 && c2 == c1 - 1) type = -2; // left
    else if (r2 == r1 && c2 == c1 + 1) type = -1; // right
    
    if (type != -100) {
        add_op(type, r1 + 1, c1 + 1);
        swap(grid[r1][c1], grid[r2][c2]);
    }
}

// BFS to find path from (r1, c1) to (r2, c2) avoiding fixed cells and obstacles
bool get_path(int r1, int c1, int r2, int c2, int fixed_limit, const set<pair<int,int>>& obstacles, vector<pair<int,int>>& path) {
    if (r1 == r2 && c1 == c2) return true;
    
    int q_sz = N * M + 1;
    vector<int> parent(N * M, -1);
    vector<int> q(q_sz);
    vector<bool> vis(N * M, false);
    int head = 0, tail = 0;
    
    auto encode = [&](int r, int c) { return r * M + c; };
    auto decode = [&](int code) { return make_pair(code / M, code % M); };
    
    int start = encode(r1, c1);
    int end = encode(r2, c2);
    
    q[tail++] = start;
    vis[start] = true;
    
    int dr[] = {0, 0, 1, -1};
    int dc[] = {1, -1, 0, 0};
    
    while (head != tail) {
        int curr = q[head++];
        if (curr == end) break;
        
        pair<int,int> pos = decode(curr);
        int r = pos.first;
        int c = pos.second;
        
        for (int i = 0; i < 4; ++i) {
            int nr = r + dr[i];
            int nc = c + dc[i];
            
            if (nr >= 0 && nr < N && nc >= 0 && nc < M) {
                int next_code = encode(nr, nc);
                if (!vis[next_code]) {
                    if (next_code < fixed_limit) continue; // fixed cell
                    if (obstacles.count({nr, nc})) continue; // obstacle
                    
                    vis[next_code] = true;
                    parent[next_code] = curr;
                    q[tail++] = next_code;
                }
            }
        }
    }
    
    if (!vis[end]) return false;
    
    int cur = end;
    while (cur != start) {
        path.push_back(decode(cur));
        cur = parent[cur];
    }
    return true;
}

void move_cell(int r1, int c1, int r2, int c2, int fixed_limit, const set<pair<int,int>>& obstacles) {
    if (r1 == r2 && c1 == c2) return;
    
    vector<pair<int,int>> path;
    if (!get_path(r1, c1, r2, c2, fixed_limit, obstacles, path)) return;
    
    for (int i = path.size() - 1; i >= 0; --i) {
        perform_swap(r1, c1, path[i].first, path[i].second);
        r1 = path[i].first;
        c1 = path[i].second;
    }
}

bool solve() {
    int total_cells = N * M;
    
    for (int fixed = 0; fixed < total_cells; ++fixed) {
        int fr = fixed / M;
        int fc = fixed % M;
        
        while (true) {
            map<char, int> needed;
            map<char, int> have;
            for (int i = fixed; i < total_cells; ++i) {
                needed[target[i/M][i%M]]++;
                have[grid[i/M][i%M]]++;
            }
            
            char missing_char = 0;
            for (auto const& [key, val] : needed) {
                if (have[key] < val) {
                    missing_char = key;
                    break;
                }
            }
            
            if (missing_char == 0) break;
            
            bool spawned = false;
            
            for (const auto& p : presets) {
                vector<pair<int,int>> char_locs;
                for(int r=0; r<p.h; ++r) 
                    for(int c=0; c<p.w; ++c)
                        if(p.mat[r][c] == missing_char) char_locs.push_back({r,c});
                
                if (char_locs.empty()) continue;
                
                for (int pr = 0; pr <= N - p.h; ++pr) {
                    for (int pc = 0; pc <= M - p.w; ++pc) {
                        bool conflict = false;
                        for (int rr = 0; rr < p.h; ++rr) {
                            for (int cc = 0; cc < p.w; ++cc) {
                                int global_idx = (pr + rr) * M + (pc + cc);
                                if (global_idx < fixed) {
                                    conflict = true; 
                                    break;
                                }
                            }
                            if (conflict) break;
                        }
                        if (conflict) continue;
                        
                        bool evac_success = true;
                        while(true) {
                            int crit_r = -1, crit_c = -1;
                            for (int rr = 0; rr < p.h; ++rr) {
                                for (int cc = 0; cc < p.w; ++cc) {
                                    char c_cur = grid[pr + rr][pc + cc];
                                    char c_new = p.mat[rr][cc];
                                    if (c_cur == c_new) continue;
                                    
                                    if (have[c_cur] <= needed[c_cur]) {
                                        crit_r = pr + rr;
                                        crit_c = pc + cc;
                                        goto found_crit;
                                    }
                                }
                            }
                            break;
                            
                            found_crit:;
                            int garb_r = -1, garb_c = -1;
                            for (int i = fixed; i < total_cells; ++i) {
                                int r = i / M;
                                int c = i % M;
                                if (r >= pr && r < pr + p.h && c >= pc && c < pc + p.w) continue;
                                if (have[grid[r][c]] > needed[grid[r][c]]) {
                                    garb_r = r;
                                    garb_c = c;
                                    break;
                                }
                            }
                            
                            if (garb_r == -1) {
                                evac_success = false;
                                break;
                            }
                            
                            set<pair<int,int>> obs; 
                            move_cell(crit_r, crit_c, garb_r, garb_c, fixed, obs);
                        }
                        
                        if (evac_success) {
                            add_op(p.id, pr + 1, pc + 1);
                            for(int rr=0; rr<p.h; ++rr)
                                for(int cc=0; cc<p.w; ++cc)
                                    grid[pr+rr][pc+cc] = p.mat[rr][cc];
                            
                            spawned = true;
                            goto spawned_label;
                        }
                    }
                }
            }
            spawned_label:;
            
            if (!spawned) return false;
        }
        
        char target_c = target[fr][fc];
        int best_r = -1, best_c = -1, min_dist = 10000;
        
        for (int i = fixed; i < total_cells; ++i) {
            int r = i / M;
            int c = i % M;
            if (grid[r][c] == target_c) {
                int dist = abs(r - fr) + abs(c - fc);
                if (dist < min_dist) {
                    min_dist = dist;
                    best_r = r;
                    best_c = c;
                }
            }
        }
        
        if (best_r == -1) return false;
        
        set<pair<int,int>> obs;
        move_cell(best_r, best_c, fr, fc, fixed, obs);
    }
    
    return true;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N >> M >> K)) return 0;
    
    grid.resize(N);
    for (int i = 0; i < N; ++i) cin >> grid[i];
    
    target.resize(N);
    for (int i = 0; i < N; ++i) cin >> target[i];
    
    presets.resize(K);
    for (int i = 0; i < K; ++i) {
        int np, mp;
        cin >> np >> mp;
        presets[i].h = np;
        presets[i].w = mp;
        presets[i].mat.resize(np);
        presets[i].id = i + 1;
        for (int r = 0; r < np; ++r) cin >> presets[i].mat[r];
    }
    
    if (solve()) {
        cout << operations.size() << "\n";
        for (const auto& op : operations) {
            cout << op.type << " " << op.x << " " << op.y << "\n";
        }
    } else {
        cout << "-1\n";
    }
    
    return 0;
}