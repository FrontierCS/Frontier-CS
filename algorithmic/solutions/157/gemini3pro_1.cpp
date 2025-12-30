#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <map>
#include <algorithm>
#include <random>
#include <chrono>
#include <cassert>

using namespace std;

// Direction constants: 0=Left, 1=Up, 2=Right, 3=Down
const int DR[] = {0, -1, 0, 1};
const int DC[] = {-1, 0, 1, 0};
const char DIR_CHAR[] = {'L', 'U', 'R', 'D'};

int N, T;
vector<vector<int>> initial_board;
int tile_counts[16];

// Bitmasks: 1=Left, 2=Up, 4=Right, 8=Down
bool has_left(int tile) { return (tile & 1); }
bool has_up(int tile) { return (tile & 2); }
bool has_right(int tile) { return (tile & 4); }
bool has_down(int tile) { return (tile & 8); }

chrono::steady_clock::time_point start_time;
vector<vector<int>> best_target;

// DSU for tree checking
struct DSU {
    vector<int> parent;
    DSU(int n) : parent(n) {
        for(int i=0; i<n; ++i) parent[i] = i;
    }
    int find(int x) {
        if(parent[x] == x) return x;
        return parent[x] = find(parent[x]);
    }
    bool unite(int x, int y) {
        int rootX = find(x);
        int rootY = find(y);
        if(rootX != rootY) {
            parent[rootX] = rootY;
            return true;
        }
        return false;
    }
};

bool is_tree(const vector<vector<int>>& board) {
    DSU dsu(N*N);
    int edges = 0;
    for(int r=0; r<N; ++r) {
        for(int c=0; c<N; ++c) {
            if (board[r][c] == 0) continue;
            if (has_right(board[r][c])) {
                if (c+1 >= N || !has_left(board[r][c+1])) return false;
                int u = r*N + c;
                int v = r*N + (c+1);
                if (dsu.find(u) == dsu.find(v)) return false;
                dsu.unite(u, v);
                edges++;
            }
            if (has_down(board[r][c])) {
                if (r+1 >= N || !has_up(board[r+1][c])) return false;
                int u = r*N + c;
                int v = (r+1)*N + c;
                if (dsu.find(u) == dsu.find(v)) return false;
                dsu.unite(u, v);
                edges++;
            }
        }
    }
    return edges == N*N - 2;
}

bool is_valid(int r, int c, int tile, const vector<vector<int>>& board) {
    if (tile == 0) return true;
    if (r == 0 && has_up(tile)) return false;
    if (r == N-1 && has_down(tile)) return false;
    if (c == 0 && has_left(tile)) return false;
    if (c == N-1 && has_right(tile)) return false;
    if (r > 0 && board[r-1][c] != 0 && (has_down(board[r-1][c]) != has_up(tile))) return false;
    if (c > 0 && board[r][c-1] != 0 && (has_right(board[r][c-1]) != has_left(tile))) return false;
    if (r == N-2 && c == N-1 && has_down(tile)) return false;
    if (r == N-1 && c == N-2 && has_right(tile)) return false;
    return true;
}

bool solve_csp(int r, int c, vector<int>& counts, vector<vector<int>>& board) {
    auto now = chrono::steady_clock::now();
    if (chrono::duration_cast<chrono::milliseconds>(now - start_time).count() > 1800) return false;

    if (r == N) return is_tree(board);
    
    int next_r = c == N-1 ? r + 1 : r;
    int next_c = c == N-1 ? 0 : c + 1;

    if (r == N-1 && c == N-1) {
        board[r][c] = 0;
        return counts[0] > 0 ? solve_csp(next_r, next_c, counts, board) : false;
    }

    int req_up = (r > 0) ? (has_down(board[r-1][c]) ? 1 : 0) : 0;
    int req_left = (c > 0) ? (has_right(board[r][c-1]) ? 1 : 0) : 0;

    vector<int> candidates;
    for (int t = 1; t < 16; ++t) {
        if (counts[t] > 0) {
            if ((has_up(t) == req_up) && (has_left(t) == req_left) && is_valid(r, c, t, board)) {
                candidates.push_back(t);
            }
        }
    }
    
    static mt19937 rng(0);
    shuffle(candidates.begin(), candidates.end(), rng);

    for (int t : candidates) {
        board[r][c] = t;
        counts[t]--;
        if (solve_csp(next_r, next_c, counts, board)) return true;
        counts[t]++;
        board[r][c] = 0;
    }
    return false;
}

string moves_str = "";
int cur_empty_r, cur_empty_c;

void record_move(char m) {
    moves_str += m;
    int dr = 0, dc = 0;
    if (m == 'L') dc = -1;
    else if (m == 'U') dr = -1;
    else if (m == 'R') dc = 1;
    else if (m == 'D') dr = 1;
    cur_empty_r += dr;
    cur_empty_c += dc;
}

bool move_empty_to(int tr, int tc, const vector<vector<bool>>& blocked) {
    if (cur_empty_r == tr && cur_empty_c == tc) return true;
    queue<pair<int, int>> q;
    q.push({cur_empty_r, cur_empty_c});
    vector<vector<pair<int, int>>> parent(N, vector<pair<int, int>>(N, {-1, -1}));
    vector<vector<char>> move_char(N, vector<char>(N, 0));
    vector<vector<bool>> visited(N, vector<bool>(N, false));
    visited[cur_empty_r][cur_empty_c] = true;
    bool found = false;
    while(!q.empty()) {
        auto [r, c] = q.front(); q.pop();
        if (r == tr && c == tc) { found = true; break; }
        for(int k=0; k<4; ++k) {
            int nr = r + DR[k], nc = c + DC[k];
            if (nr >= 0 && nr < N && nc >= 0 && nc < N && !visited[nr][nc] && !blocked[nr][nc]) {
                visited[nr][nc] = true;
                parent[nr][nc] = {r, c};
                move_char[nr][nc] = DIR_CHAR[k];
                q.push({nr, nc});
            }
        }
    }
    if (!found) return false;
    string path = "";
    int r = tr, c = tc;
    while(r != cur_empty_r || c != cur_empty_c) {
        path += move_char[r][c];
        auto p = parent[r][c];
        r = p.first; c = p.second;
    }
    reverse(path.begin(), path.end());
    for(char c : path) record_move(c);
    return true;
}

void move_tile(int sr, int sc, int dr, int dc, vector<vector<int>>& current_board, vector<vector<bool>>& blocked) {
    queue<pair<int, int>> q;
    q.push({sr, sc});
    vector<vector<pair<int, int>>> parent(N, vector<pair<int, int>>(N, {-1, -1}));
    vector<vector<bool>> visited(N, vector<bool>(N, false));
    visited[sr][sc] = true;
    bool found = false;
    while(!q.empty()) {
        auto [r, c] = q.front(); q.pop();
        if (r == dr && c == dc) { found = true; break; }
        for(int k=0; k<4; ++k) {
            int nr = r + DR[k], nc = c + DC[k];
            if (nr >= 0 && nr < N && nc >= 0 && nc < N && !visited[nr][nc] && !blocked[nr][nc]) {
                visited[nr][nc] = true;
                parent[nr][nc] = {r, c};
                q.push({nr, nc});
            }
        }
    }
    vector<pair<int, int>> path;
    int r = dr, c = dc;
    while(r != sr || c != sc) {
        path.push_back({r, c});
        auto p = parent[r][c];
        r = p.first; c = p.second;
    }
    reverse(path.begin(), path.end());
    int curr_r = sr, curr_c = sc;
    for(auto next_pos : path) {
        int nr = next_pos.first, nc = next_pos.second;
        blocked[curr_r][curr_c] = true;
        move_empty_to(nr, nc, blocked);
        blocked[curr_r][curr_c] = false;
        int slide_dir = -1;
        for(int k=0; k<4; ++k) if (nr + DR[k] == curr_r && nc + DC[k] == curr_c) slide_dir = k;
        record_move(DIR_CHAR[slide_dir]);
        swap(current_board[curr_r][curr_c], current_board[nr][nc]);
        curr_r = nr; curr_c = nc;
    }
}

int main() {
    start_time = chrono::steady_clock::now();
    cin >> N >> T;
    initial_board.resize(N, vector<int>(N));
    vector<int> counts(16, 0);
    for(int i=0; i<N; ++i) {
        string s; cin >> s;
        for(int j=0; j<N; ++j) {
            char c = s[j];
            int val = (c >= '0' && c <= '9') ? c - '0' : c - 'a' + 10;
            initial_board[i][j] = val;
            counts[val]++;
            if (val == 0) { cur_empty_r = i; cur_empty_c = j; }
        }
    }

    best_target.resize(N, vector<int>(N));
    vector<vector<int>> board(N, vector<int>(N));
    if (!solve_csp(0, 0, counts, board)) return 0;
    best_target = board;

    vector<pair<int, int>> src_pos[16], tgt_pos[16];
    for(int r=0; r<N; ++r) for(int c=0; c<N; ++c) {
        src_pos[initial_board[r][c]].push_back({r, c});
        tgt_pos[best_target[r][c]].push_back({r, c});
    }

    map<int, pair<int, int>> assignment;
    for(int t=0; t<16; ++t) {
        if (src_pos[t].empty()) continue;
        vector<bool> used_tgt(src_pos[t].size(), false);
        for(size_t i=0; i<src_pos[t].size(); ++i) {
            int best_j = -1, min_dist = 1e9;
            for(size_t j=0; j<tgt_pos[t].size(); ++j) {
                if (used_tgt[j]) continue;
                int d = abs(src_pos[t][i].first - tgt_pos[t][j].first) + abs(src_pos[t][i].second - tgt_pos[t][j].second);
                if (d < min_dist) { min_dist = d; best_j = j; }
            }
            used_tgt[best_j] = true;
            assignment[src_pos[t][i].first * N + src_pos[t][i].second] = tgt_pos[t][best_j];
        }
    }

    vector<int> p;
    for(int r=0; r<N; ++r) for(int c=0; c<N; ++c) {
        if (initial_board[r][c] == 0) continue;
        pair<int, int> tgt = assignment[r*N+c];
        p.push_back(tgt.first * N + tgt.second);
    }
    int inversions = 0;
    for(size_t i=0; i<p.size(); ++i) for(size_t j=i+1; j<p.size(); ++j) if (p[i] > p[j]) inversions++;
    int dist = abs(cur_empty_r - (N-1)) + abs(cur_empty_c - (N-1));
    if ((inversions + dist) % 2 != 0) {
        for(int t=1; t<16; ++t) {
            if (src_pos[t].size() >= 2) {
                int s1 = src_pos[t][0].first * N + src_pos[t][0].second;
                int s2 = src_pos[t][1].first * N + src_pos[t][1].second;
                swap(assignment[s1], assignment[s2]);
                break;
            }
        }
    }

    vector<vector<int>> current_ids(N, vector<int>(N)), target_ids(N, vector<int>(N, -1));
    for(int r=0; r<N; ++r) for(int c=0; c<N; ++c) {
        current_ids[r][c] = r*N + c;
        if (initial_board[r][c] != 0) {
            pair<int, int> tgt = assignment[r*N+c];
            target_ids[tgt.first][tgt.second] = r*N + c;
        }
    }

    vector<vector<bool>> blocked(N, vector<bool>(N, false));
    for(int phase_r = 0; phase_r < N - 2; ++phase_r) {
        for(int c = 0; c < N; ++c) {
            if (c < N - 2) {
                int t = target_ids[phase_r][c];
                int sr=-1, sc=-1;
                for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) if(current_ids[i][j] == t) { sr=i; sc=j; }
                move_tile(sr, sc, phase_r, c, current_ids, blocked);
                blocked[phase_r][c] = true;
            } else if (c == N - 2) {
                int t1 = target_ids[phase_r][N-2], t2 = target_ids[phase_r][N-1];
                int sr=-1, sc=-1;
                for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) if(current_ids[i][j] == t2) { sr=i; sc=j; }
                move_tile(sr, sc, phase_r+1, N-1, current_ids, blocked);
                blocked[phase_r+1][N-1] = true;
                for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) if(current_ids[i][j] == t1) { sr=i; sc=j; }
                move_tile(sr, sc, phase_r, N-1, current_ids, blocked);
                blocked[phase_r][N-1] = true;
                blocked[phase_r+1][N-1] = false; blocked[phase_r][N-1] = false;
                blocked[phase_r][N-1] = true; blocked[phase_r+1][N-1] = true;
                move_empty_to(phase_r, N-2, blocked);
                blocked[phase_r][N-1] = false; blocked[phase_r+1][N-1] = false;
                record_move('L'); swap(current_ids[phase_r][N-2], current_ids[phase_r][N-1]); cur_empty_c++;
                record_move('D'); swap(current_ids[phase_r][N-1], current_ids[phase_r+1][N-1]); cur_empty_r++;
                blocked[phase_r][N-2] = true; blocked[phase_r][N-1] = true;
                c++;
            }
        }
    }
    for(int phase_c = 0; phase_c < N - 2; ++phase_c) {
         for(int r = N - 2; r < N; ++r) {
             if (r == N - 2) {
                 int t1 = target_ids[N-2][phase_c], t2 = target_ids[N-1][phase_c];
                 int sr=-1, sc=-1;
                 for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) if(current_ids[i][j] == t2) { sr=i; sc=j; }
                 move_tile(sr, sc, N-1, phase_c + 1, current_ids, blocked);
                 blocked[N-1][phase_c+1] = true;
                 for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) if(current_ids[i][j] == t1) { sr=i; sc=j; }
                 move_tile(sr, sc, N-1, phase_c, current_ids, blocked);
                 blocked[N-1][phase_c+1] = false;
                 blocked[N-1][phase_c] = true; blocked[N-1][phase_c+1] = true;
                 move_empty_to(N-2, phase_c, blocked);
                 blocked[N-1][phase_c] = false; blocked[N-1][phase_c+1] = false;
                 record_move('D'); swap(current_ids[N-2][phase_c], current_ids[N-1][phase_c]); cur_empty_r++;
                 record_move('R'); swap(current_ids[N-1][phase_c], current_ids[N-1][phase_c+1]); cur_empty_c++;
                 blocked[N-2][phase_c] = true; blocked[N-1][phase_c] = true;
                 break;
             }
         }
    }
    
    int empty_id = current_ids[cur_empty_r][cur_empty_c];
    vector<pair<int, int>> cells = {{N-2, N-2}, {N-2, N-1}, {N-1, N-2}, {N-1, N-1}};
    vector<int> desired(4);
    for(int i=0; i<4; ++i) {
        int t = target_ids[cells[i].first][cells[i].second];
        desired[i] = (t == -1) ? empty_id : t;
    }
    
    map<vector<int>, string> dist;
    vector<int> start_state(4);
    for(int i=0; i<4; ++i) start_state[i] = current_ids[cells[i].first][cells[i].second];
    queue<vector<int>> q2; q2.push(start_state); dist[start_state] = "";
    while(!q2.empty()) {
        vector<int> s = q2.front(); q2.pop();
        if (s == desired) { for(char c : dist[s]) record_move(c); break; }
        int idx = -1; for(int i=0; i<4; ++i) if(s[i] == empty_id) idx = i;
        if(dist[s].length() > 20) continue;
        for(int k=0; k<4; ++k) {
            int nr = cells[idx].first + DR[k], nc = cells[idx].second + DC[k];
            if (nr >= N-2 && nr < N && nc >= N-2 && nc < N) {
                int nidx = -1; for(int i=0; i<4; ++i) if(cells[i].first == nr && cells[i].second == nc) nidx = i;
                vector<int> next_s = s; swap(next_s[idx], next_s[nidx]);
                if (dist.find(next_s) == dist.end()) { dist[next_s] = dist[s] + DIR_CHAR[k]; q2.push(next_s); }
            }
        }
    }
    cout << moves_str << endl;
    return 0;
}