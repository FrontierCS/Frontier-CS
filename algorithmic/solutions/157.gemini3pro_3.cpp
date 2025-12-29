#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <map>
#include <queue>
#include <random>
#include <chrono>
#include <set>
#include <cassert>

using namespace std;

int N, T;
int grid_init[10][10];
int target_grid[10][10];
int counts[16];
int target_counts[16];
string solution_moves = "";

const int dr[] = {0, -1, 0, 1};
const int dc[] = {-1, 0, 1, 0};
const char dir_chars[] = {'L', 'U', 'R', 'D'};

mt19937 rng(12345);

auto start_time = chrono::high_resolution_clock::now();
double get_time() {
    auto now = chrono::high_resolution_clock::now();
    return chrono::duration<double>(now - start_time).count();
}

struct Edge {
    int u, v;
};

int idx(int r, int c) { return r * N + c; }

void generate_target() {
    vector<vector<int>> adj(N*N);
    vector<Edge> tree_edges;
    
    for(int r=0; r<N; ++r) {
        for(int c=0; c<N; ++c) {
            if(r==N-1 && c==N-1) continue;
            int u = idx(r, c);
            for(int d=0; d<4; ++d) {
                int nr = r + dr[d];
                int nc = c + dc[d];
                if(nr>=0 && nr<N && nc>=0 && nc<N && !(nr==N-1 && nc==N-1)) {
                    adj[u].push_back(idx(nr, nc));
                }
            }
        }
    }
    
    vector<int> stack;
    vector<int> visited(N*N, 0);
    stack.push_back(0);
    visited[0] = 1;
    while(!stack.empty()) {
        int u = stack.back();
        vector<int> neighbors;
        for(int v : adj[u]) {
            if(!visited[v]) neighbors.push_back(v);
        }
        if(neighbors.empty()) {
            stack.pop_back();
        } else {
            int v = neighbors[rng() % neighbors.size()];
            visited[v] = 1;
            tree_edges.push_back({u, v});
            stack.push_back(v);
        }
    }

    set<pair<int,int>> current_edges;
    for(auto& e : tree_edges) {
        if(e.u > e.v) swap(e.u, e.v);
        current_edges.insert({e.u, e.v});
    }

    auto calc_score = [&]() {
        fill(target_counts, target_counts+16, 0);
        int score = 0;
        for(int r=0; r<N; ++r) {
            for(int c=0; c<N; ++c) {
                if(r==N-1 && c==N-1) continue;
                int mask = 0;
                int u = idx(r, c);
                for(int d=0; d<4; ++d) {
                    int nr = r + dr[d];
                    int nc = c + dc[d];
                    if(nr>=0 && nr<N && nc>=0 && nc<N && !(nr==N-1 && nc==N-1)) {
                        int v = idx(nr, nc);
                        int u_ = u, v_ = v;
                        if(u_ > v_) swap(u_, v_);
                        if(current_edges.count({u_, v_})) {
                            mask |= (1 << d);
                        }
                    }
                }
                target_counts[mask]++;
            }
        }
        for(int i=1; i<16; ++i) score += abs(target_counts[i] - counts[i]);
        return score;
    };

    int current_score = calc_score();
    
    while(get_time() < 1.0 && current_score > 0) {
        if(current_edges.empty()) break; 
        auto it = current_edges.begin();
        advance(it, rng() % current_edges.size());
        pair<int, int> rem_edge = *it;
        
        current_edges.erase(it);
        
        vector<int> q;
        q.push_back(rem_edge.first);
        vector<int> comp(N*N, 0);
        comp[rem_edge.first] = 1;
        int head = 0;
        while(head < q.size()){
            int u = q[head++];
            for(int v : adj[u]) {
                int u_ = u, v_ = v;
                if(u_ > v_) swap(u_, v_);
                if(current_edges.count({u_, v_})) {
                    if(comp[v] == 0) {
                        comp[v] = 1;
                        q.push_back(v);
                    }
                }
            }
        }
        
        vector<pair<int,int>> candidates;
        for(int u : q) {
            for(int v : adj[u]) {
                if(comp[v] == 0) {
                    candidates.push_back({min(u,v), max(u,v)});
                }
            }
        }
        
        if(!candidates.empty()) {
            pair<int,int> add_edge = candidates[rng() % candidates.size()];
            current_edges.insert(add_edge);
            
            int new_score = calc_score();
            if(new_score <= current_score) {
                current_score = new_score;
            } else {
                current_edges.erase(add_edge);
                current_edges.insert(rem_edge);
                calc_score();
            }
        } else {
             current_edges.insert(rem_edge);
        }
    }

    for(int r=0; r<N; ++r) {
        for(int c=0; c<N; ++c) target_grid[r][c] = 0;
    }
    for(int r=0; r<N; ++r) {
        for(int c=0; c<N; ++c) {
            if(r==N-1 && c==N-1) continue;
            int mask = 0;
            int u = idx(r, c);
            for(int d=0; d<4; ++d) {
                int nr = r + dr[d];
                int nc = c + dc[d];
                if(nr>=0 && nr<N && nc>=0 && nc<N && !(nr==N-1 && nc==N-1)) {
                    int v = idx(nr, nc);
                    int u_ = u, v_ = v;
                    if(u_ > v_) swap(u_, v_);
                    if(current_edges.count({u_, v_})) {
                        mask |= (1 << d);
                    }
                }
            }
            target_grid[r][c] = mask;
        }
    }
}

int cur_grid[10][10];
bool locked[10][10];
int empty_r, empty_c;

void move_empty(int tr, int tc) {
    while(empty_r != tr || empty_c != tc) {
        queue<pair<int,int>> q;
        q.push({empty_r, empty_c});
        pair<int,int> parent[10][10];
        for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) parent[i][j] = {-1,-1};
        parent[empty_r][empty_c] = {-2, -2};
        
        bool found = false;
        while(!q.empty()) {
            auto [r, c] = q.front(); q.pop();
            if(r == tr && c == tc) { found = true; break; }
            
            for(int i=0; i<4; ++i) {
                int nr = r + dr[i];
                int nc = c + dc[i];
                if(nr>=0 && nr<N && nc>=0 && nc<N && !locked[nr][nc]) {
                    if(parent[nr][nc].first == -1) {
                        parent[nr][nc] = {r, c};
                        q.push({nr, nc});
                    }
                }
            }
        }
        
        if(!found) return;
        
        vector<pair<int,int>> path;
        int curr = tr, curc = tc;
        while(curr != empty_r || curc != empty_c) {
            path.push_back({curr, curc});
            auto p = parent[curr][curc];
            curr = p.first;
            curc = p.second;
        }
        auto [next_r, next_c] = path.back();
        
        for(int i=0; i<4; ++i) {
            if(empty_r + dr[i] == next_r && empty_c + dc[i] == next_c) {
                solution_moves += dir_chars[i];
                swap(cur_grid[empty_r][empty_c], cur_grid[next_r][next_c]);
                empty_r = next_r;
                empty_c = next_c;
                break;
            }
        }
    }
}

void move_tile(int fr, int fc, int tr, int tc) {
    if(fr == tr && fc == tc) return;
    
    while(fr != tr || fc != tc) {
        queue<pair<int,int>> q;
        q.push({fr, fc});
        pair<int,int> parent[10][10];
        for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) parent[i][j] = {-1,-1};
        parent[fr][fc] = {-2, -2};
        
        bool found = false;
        while(!q.empty()) {
            auto [r, c] = q.front(); q.pop();
            if(r == tr && c == tc) { found = true; break; }
            
            for(int i=0; i<4; ++i) {
                int nr = r + dr[i];
                int nc = c + dc[i];
                if(nr>=0 && nr<N && nc>=0 && nc<N && !locked[nr][nc]) {
                    if(parent[nr][nc].first == -1) {
                        parent[nr][nc] = {r, c};
                        q.push({nr, nc});
                    }
                }
            }
        }
        
        if(!found) return;
        
        vector<pair<int,int>> path;
        int curr = tr, curc = tc;
        while(curr != fr || curc != fc) {
            path.push_back({curr, curc});
            auto p = parent[curr][curc];
            curr = p.first;
            curc = p.second;
        }
        auto [next_r, next_c] = path.back();
        
        locked[fr][fc] = true;
        move_empty(next_r, next_c);
        locked[fr][fc] = false;
        
        for(int i=0; i<4; ++i) {
            if(empty_r + dr[i] == fr && empty_c + dc[i] == fc) {
                solution_moves += dir_chars[i];
                swap(cur_grid[empty_r][empty_c], cur_grid[fr][fc]);
                empty_r = fr;
                empty_c = fc;
                fr = next_r;
                fc = next_c;
                break;
            }
        }
    }
}

void solve() {
    for(int r=0; r<N; ++r) for(int c=0; c<N; ++c) {
        cur_grid[r][c] = grid_init[r][c];
        if(cur_grid[r][c] == 0) { empty_r = r; empty_c = c; }
        locked[r][c] = false;
    }

    auto find_tile = [&](int t, int r_start, int c_start) -> pair<int, int> {
        int best_r = -1, best_c = -1, min_d = 1e9;
        for(int r=0; r<N; ++r) {
            for(int c=0; c<N; ++c) {
                if(!locked[r][c] && cur_grid[r][c] == t) {
                     int d = abs(r - r_start) + abs(c - c_start);
                     if(d < min_d) {
                         min_d = d;
                         best_r = r;
                         best_c = c;
                     }
                }
            }
        }
        return {best_r, best_c};
    };

    for(int r=0; r<=N-3; ++r) {
        for(int c=0; c<=N-3; ++c) {
            int target_type = target_grid[r][c];
            pair<int,int> p = find_tile(target_type, r, c);
            if(p.first == -1) {
                for(int rr=0; rr<N; ++rr) for(int cc=0; cc<N; ++cc) {
                     if(!locked[rr][cc]) { p={rr,cc}; goto found1; }
                }
                found1:;
            }
            move_tile(p.first, p.second, r, c);
            locked[r][c] = true;
        }
        
        int typeA = target_grid[r][N-2];
        int typeB = target_grid[r][N-1];
        
        pair<int,int> pA = find_tile(typeA, r, N-2);
        if(pA.first == -1) {
            for(int rr=0; rr<N; ++rr) for(int cc=0; cc<N; ++cc) {
                 if(!locked[rr][cc]) { pA={rr,cc}; goto found2; }
            }
            found2:;
        }
        move_tile(pA.first, pA.second, r, N-1);
        locked[r][N-1] = true;
        
        pair<int,int> pB = find_tile(typeB, r+1, N-1);
        if(pB.first == -1) {
            for(int rr=0; rr<N; ++rr) for(int cc=0; cc<N; ++cc) {
                 if(!locked[rr][cc]) { pB={rr,cc}; goto found3; }
            }
            found3:;
        }
        move_tile(pB.first, pB.second, r+1, N-1);
        
        locked[r][N-1] = false;
        
        locked[r][N-1] = true; 
        locked[r+1][N-1] = true;
        move_empty(r, N-2);
        locked[r][N-1] = false;
        locked[r+1][N-1] = false;
        
        if(empty_r == r && empty_c == N-2) {
             solution_moves += "R"; 
             swap(cur_grid[r][N-2], cur_grid[r][N-1]);
             empty_c = N-1;
        } else {
             move_tile(r, N-1, r, N-2); 
        }
        
        if(empty_r == r && empty_c == N-1) {
             solution_moves += "D"; 
             swap(cur_grid[r][N-1], cur_grid[r+1][N-1]);
             empty_r = r+1;
        } else {
             move_tile(r+1, N-1, r, N-1);
        }
        
        locked[r][N-2] = true;
        locked[r][N-1] = true;
    }
    
    for(int c=0; c<=N-3; ++c) {
        int typeA = target_grid[N-2][c];
        int typeB = target_grid[N-1][c];
        
        pair<int,int> pA = find_tile(typeA, N-2, c);
        if(pA.first == -1) {
            for(int rr=0; rr<N; ++rr) for(int cc=0; cc<N; ++cc) {
                 if(!locked[rr][cc]) { pA={rr,cc}; goto found4; }
            }
            found4:;
        }
        move_tile(pA.first, pA.second, N-1, c);
        locked[N-1][c] = true;
        
        pair<int,int> pB = find_tile(typeB, N-1, c+1);
        if(pB.first == -1) {
            for(int rr=0; rr<N; ++rr) for(int cc=0; cc<N; ++cc) {
                 if(!locked[rr][cc]) { pB={rr,cc}; goto found5; }
            }
            found5:;
        }
        move_tile(pB.first, pB.second, N-1, c+1);
        locked[N-1][c] = false;
        
        locked[N-1][c] = true;
        locked[N-1][c+1] = true;
        move_empty(N-2, c);
        locked[N-1][c] = false;
        locked[N-1][c+1] = false;
        
        if(empty_r == N-2 && empty_c == c) {
            solution_moves += "D";
            swap(cur_grid[N-2][c], cur_grid[N-1][c]);
            empty_r = N-1;
        }
        if(empty_r == N-1 && empty_c == c) {
            solution_moves += "R";
            swap(cur_grid[N-1][c], cur_grid[N-1][c+1]);
            empty_c = c+1;
        }
        
        locked[N-2][c] = true;
        locked[N-1][c] = true;
    }
    
    move_empty(N-1, N-1);
    
    int rots = 0;
    while(rots < 8) {
        bool ok = true;
        if(cur_grid[N-2][N-2] != target_grid[N-2][N-2]) ok = false;
        if(cur_grid[N-2][N-1] != target_grid[N-2][N-1]) ok = false;
        if(cur_grid[N-1][N-2] != target_grid[N-1][N-2]) ok = false;
        
        if(ok) break;
        
        string cycle = "LURD";
        for(char m : cycle) {
            solution_moves += m;
            int dir = -1;
            if(m=='L') dir=0; else if(m=='U') dir=1; else if(m=='R') dir=2; else dir=3;
            int nr = empty_r + dr[dir];
            int nc = empty_c + dc[dir];
            swap(cur_grid[empty_r][empty_c], cur_grid[nr][nc]);
            empty_r = nr; empty_c = nc;
        }
        rots++;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    cin >> N >> T;
    fill(counts, counts+16, 0);
    for(int i=0; i<N; ++i) {
        string s; cin >> s;
        for(int j=0; j<N; ++j) {
            int val;
            if(isdigit(s[j])) val = s[j] - '0';
            else val = s[j] - 'a' + 10;
            grid_init[i][j] = val;
            counts[val]++;
        }
    }
    
    generate_target();
    solve();
    
    if (solution_moves.length() > T) {
        solution_moves = solution_moves.substr(0, T);
    }
    
    cout << solution_moves << endl;
    return 0;
}