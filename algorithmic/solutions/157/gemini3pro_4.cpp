#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <queue>
#include <cmath>
#include <cstdlib>
#include <ctime>

using namespace std;

int N, T_limit;
int board[10][10];
int target[10][10];
int counts[16];
bool fixed_cell[10][10];
string moves_str = "";

// Disjoint Set Union for cycle detection
struct DSU {
    int parent[100];
    vector<pair<int, int>> history;

    void init() {
        for(int i=0; i<N*N; ++i) parent[i] = i;
        history.clear();
    }

    int find(int i) {
        if (parent[i] == i) return i;
        return find(parent[i]);
    }

    bool unite(int i, int j) {
        int root_i = find(i);
        int root_j = find(j);
        if (root_i != root_j) {
            history.push_back({root_i, parent[root_i]});
            parent[root_i] = root_j;
            return true;
        }
        return false;
    }

    void rollback(int snapshot) {
        while (history.size() > snapshot) {
            auto p = history.back();
            history.pop_back();
            parent[p.first] = p.second;
        }
    }
} dsu;

// Find a valid target configuration
bool solve_layout(int idx) {
    if (idx == N * N) return true;
    
    int r = idx / N;
    int c = idx % N;
    
    int req_u = (r > 0 && (target[r-1][c] & 8)) ? 1 : 0;
    int req_l = (c > 0 && (target[r][c-1] & 4)) ? 1 : 0;
    
    if (idx == N * N - 1) {
        if (req_u == 0 && req_l == 0) {
            target[r][c] = 0;
            return true;
        }
        return false;
    }

    vector<int> candidates;
    for(int t=1; t<16; ++t) {
        if (counts[t] > 0) candidates.push_back(t);
    }
    
    // Random shuffle for variety
    for (size_t i = 0; i < candidates.size(); ++i) { 
        size_t j = i + rand() % (candidates.size() - i);
        swap(candidates[i], candidates[j]);
    }

    for (int t : candidates) {
        bool up_match = (t & 2) ? true : false;
        bool left_match = (t & 1) ? true : false;
        
        if (up_match != (req_u == 1)) continue;
        if (left_match != (req_l == 1)) continue;
        
        if (r == N-1 && (t & 8)) continue;
        if (c == N-1 && (t & 4)) continue;
        
        int snapshot = dsu.history.size();
        bool ok = true;
        if (up_match) {
            if (!dsu.unite(idx, (r-1)*N + c)) ok = false;
        }
        if (ok && left_match) {
            if (!dsu.unite(idx, r*N + c - 1)) ok = false;
        }
        
        if (ok) {
            target[r][c] = t;
            counts[t]--;
            if (solve_layout(idx + 1)) return true;
            counts[t]++;
        }
        
        dsu.rollback(snapshot);
    }
    
    return false;
}

void apply_move(char c) {
    moves_str += c;
    int er, ec;
    for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) if(board[i][j] == 0) { er=i; ec=j; }
    
    int nr = er, nc = ec;
    if (c == 'U') nr--; 
    else if (c == 'D') nr++;
    else if (c == 'L') nc--;
    else if (c == 'R') nc++;
    
    // Note: The problem statement says "slide an adjacent tile... into the empty square".
    // "U" means sliding the upward tile DOWN into the empty square.
    // So if empty is at (r, c), upward tile is at (r-1, c).
    // After op, tile is at (r, c), empty is at (r-1, c).
    // So Empty moves UP.
    // My nr/nc calculation above: U -> nr = er-1. Correct.
    
    swap(board[er][ec], board[nr][nc]);
}

string get_path(int tr, int tc) {
    int er, ec;
    for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) if(board[i][j] == 0) { er=i; ec=j; }
    
    if (er == tr && ec == tc) return "";
    
    queue<pair<int, string>> q;
    q.push({er*N+ec, ""});
    vector<int> visited(N*N, 0);
    visited[er*N+ec] = 1;
    
    int dr[] = {-1, 1, 0, 0};
    int dc[] = {0, 0, -1, 1};
    char move_chars[] = {'U', 'D', 'L', 'R'};
    
    while(!q.empty()){
        auto p = q.front(); q.pop();
        int cur = p.first;
        int r = cur/N, c = cur%N;
        if (r == tr && c == tc) return p.second;
        
        for(int i=0; i<4; ++i) {
            int nr = r + dr[i];
            int nc = c + dc[i];
            if (nr>=0 && nr<N && nc>=0 && nc<N && !visited[nr*N+nc]) {
                if (!fixed_cell[nr][nc]) {
                    visited[nr*N+nc] = 1;
                    q.push({nr*N+nc, p.second + move_chars[i]});
                }
            }
        }
    }
    return "";
}

void bring_tile(int tr, int tc, int override_type = -1) {
    int type = (override_type != -1) ? override_type : target[tr][tc];
    int best_r = -1, best_c = -1, min_dist = 1000;
    
    for(int i=0; i<N; ++i) {
        for(int j=0; j<N; ++j) {
            if (!fixed_cell[i][j] && board[i][j] == type) {
                int dist = abs(i-tr) + abs(j-tc);
                if (dist < min_dist) {
                    min_dist = dist;
                    best_r = i;
                    best_c = j;
                }
            }
        }
    }
    
    int cur_r = best_r;
    int cur_c = best_c;
    
    while (cur_r != tr || cur_c != tc) {
        int next_r = cur_r, next_c = cur_c;
        if (cur_c < tc) next_c++;
        else if (cur_c > tc) next_c--;
        else if (cur_r < tr) next_r++;
        else if (cur_r > tr) next_r--;
        
        fixed_cell[cur_r][cur_c] = true;
        string p = get_path(next_r, next_c);
        fixed_cell[cur_r][cur_c] = false;
        
        for(char c : p) apply_move(c);
        
        if (next_r == cur_r - 1) apply_move('D');
        else if (next_r == cur_r + 1) apply_move('U');
        else if (next_c == cur_c - 1) apply_move('R');
        else if (next_c == cur_c + 1) apply_move('L');
        
        cur_r = next_r;
        cur_c = next_c;
    }
    fixed_cell[tr][tc] = true;
}

void solve_last_two_in_row(int r) {
    int type1 = target[r][N-2];
    int type2 = target[r][N-1];
    
    // T2 to (r, N-2)
    bring_tile(r, N-2, type2);
    
    // T1 to (r+1, N-2)
    bring_tile(r+1, N-2, type1);
    
    fixed_cell[r][N-2] = false;
    fixed_cell[r+1][N-2] = false;
    
    // Empty to (r, N-1)
    string p = get_path(r, N-1);
    for(char c : p) apply_move(c);
    
    apply_move('L');
    apply_move('D');
    
    fixed_cell[r][N-2] = true;
    fixed_cell[r][N-1] = true;
}

void solve_last_two_in_col(int c) {
    int type1 = target[N-2][c];
    int type2 = target[N-1][c];
    
    // T2 to (N-2, c)
    bring_tile(N-2, c, type2);
    
    // T1 to (N-2, c+1)
    bring_tile(N-2, c+1, type1);
    
    fixed_cell[N-2][c] = false;
    fixed_cell[N-2][c+1] = false;
    
    // Empty to (N-1, c)
    string p = get_path(N-1, c);
    for(char c : p) apply_move(c);
    
    apply_move('U');
    apply_move('R');
    
    fixed_cell[N-2][c] = true;
    fixed_cell[N-1][c] = true;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(0); 

    cin >> N >> T_limit;
    for(int i=0; i<N; ++i) {
        string s; cin >> s;
        for(int j=0; j<N; ++j) {
            char c = s[j];
            int val;
            if(c >= '0' && c <= '9') val = c - '0';
            else val = c - 'a' + 10;
            board[i][j] = val;
            counts[val]++;
        }
    }
    
    dsu.init();
    if (!solve_layout(0)) {
        // Fallback: This shouldn't happen per problem statement
    }
    
    // Solve
    for(int r=0; r<N-2; ++r) {
        for(int c=0; c<N-2; ++c) {
            bring_tile(r, c);
        }
        solve_last_two_in_row(r);
    }
    
    for(int c=0; c<N-2; ++c) {
        for(int r=N-2; r<N-2; ++r) { // Loop logic for col solving
            // Actually just solve (N-2, c) and (N-1, c)
        }
        solve_last_two_in_col(c);
    }
    
    // Final 2x2
    // Rotate until match
    int er, ec;
    for(int k=0; k<20; ++k) {
        bool match = true;
        if(board[N-2][N-2] != target[N-2][N-2]) match = false;
        if(board[N-2][N-1] != target[N-2][N-1]) match = false;
        if(board[N-1][N-2] != target[N-1][N-2]) match = false;
        if(board[N-1][N-1] != target[N-1][N-1]) match = false;
        if(match) break;
        
        // Find empty in 2x2
        for(int i=N-2; i<N; ++i) for(int j=N-2; j<N; ++j) if(board[i][j] == 0) { er=i; ec=j; }
        
        // Move empty clockwise or counter-clockwise
        // Top-Left (N-2, N-2), Top-Right (N-2, N-1)
        // Bot-Left (N-1, N-2), Bot-Right (N-1, N-1)
        if (er == N-2 && ec == N-2) apply_move('R');
        else if (er == N-2 && ec == N-1) apply_move('D');
        else if (er == N-1 && ec == N-1) apply_move('L');
        else if (er == N-1 && ec == N-2) apply_move('U');
    }
    
    cout << moves_str << endl;
    return 0;
}