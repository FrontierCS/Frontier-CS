#include <bits/stdc++.h>
using namespace std;

const int dx[4] = {0, 0, -1, 1};
const int dy[4] = {-1, 1, 0, 0};
const char dir[4] = {'L', 'R', 'U', 'D'};

int n, m;
vector<string> grid;
int sr, sc, er, ec;
int total_blank = 0;

bool inbounds(int x, int y) {
    return x >= 0 && x < n && y >= 0 && y < m;
}

bool is_blank(int x, int y) {
    return inbounds(x, y) && grid[x][y] == '1';
}

// BFS to check connectivity
bool connected() {
    vector<vector<bool>> vis(n, vector<bool>(m, false));
    queue<pair<int,int>> q;
    q.push({sr, sc});
    vis[sr][sc] = true;
    int count = 0;
    while (!q.empty()) {
        auto [x,y] = q.front(); q.pop();
        count++;
        for (int d=0; d<4; d++) {
            int nx = x + dx[d];
            int ny = y + dy[d];
            if (is_blank(nx, ny) && !vis[nx][ny]) {
                vis[nx][ny] = true;
                q.push({nx, ny});
            }
        }
    }
    return vis[er][ec];
}

// BFS to find shortest path from start to exit
string shortest_path() {
    vector<vector<bool>> vis(n, vector<bool>(m, false));
    vector<vector<pair<int,int>>> parent(n, vector<pair<int,int>>(m, {-1,-1}));
    vector<vector<int>> dir_used(n, vector<int>(m, -1));
    queue<pair<int,int>> q;
    q.push({sr, sc});
    vis[sr][sc] = true;
    while (!q.empty()) {
        auto [x,y] = q.front(); q.pop();
        if (x == er && y == ec) break;
        for (int d=0; d<4; d++) {
            int nx = x + dx[d];
            int ny = y + dy[d];
            if (is_blank(nx, ny) && !vis[nx][ny]) {
                vis[nx][ny] = true;
                parent[nx][ny] = {x,y};
                dir_used[nx][ny] = d;
                q.push({nx, ny});
            }
        }
    }
    if (!vis[er][ec]) return "";
    string path;
    int x = er, y = ec;
    while (x != sr || y != sc) {
        int d = dir_used[x][y];
        path += dir[d];
        auto p = parent[x][y];
        x = p.first;
        y = p.second;
    }
    reverse(path.begin(), path.end());
    return path;
}

// Check if a move is blocked at a cell
bool blocked_at(int x, int y, int d) {
    int nx = x + dx[d];
    int ny = y + dy[d];
    return !is_blank(nx, ny); // either out of bounds or blocked
}

// BFS to find path using only moves that are blocked at exit
string find_path_blocked_at_exit() {
    vector<vector<bool>> vis(n, vector<bool>(m, false));
    vector<vector<pair<int,int>>> parent(n, vector<pair<int,int>>(m, {-1,-1}));
    vector<vector<int>> dir_used(n, vector<int>(m, -1));
    queue<pair<int,int>> q;
    q.push({sr, sc});
    vis[sr][sc] = true;
    while (!q.empty()) {
        auto [x,y] = q.front(); q.pop();
        if (x == er && y == ec) break;
        for (int d=0; d<4; d++) {
            // Check if move d is blocked at exit
            if (!blocked_at(er, ec, d)) continue;
            int nx = x + dx[d];
            int ny = y + dy[d];
            if (is_blank(nx, ny) && !vis[nx][ny]) {
                vis[nx][ny] = true;
                parent[nx][ny] = {x,y};
                dir_used[nx][ny] = d;
                q.push({nx, ny});
            }
        }
    }
    if (!vis[er][ec]) return "";
    string path;
    int x = er, y = ec;
    while (x != sr || y != sc) {
        int d = dir_used[x][y];
        path += dir[d];
        auto p = parent[x][y];
        x = p.first;
        y = p.second;
    }
    reverse(path.begin(), path.end());
    return path;
}

// Simulate a sequence and return final position and visited set
pair<int,int> simulate(int sx, int sy, const string& seq, vector<vector<bool>>& visited) {
    int x = sx, y = sy;
    visited[x][y] = true;
    for (char c : seq) {
        int d;
        if (c == 'L') d=0;
        else if (c == 'R') d=1;
        else if (c == 'U') d=2;
        else d=3;
        int nx = x + dx[d];
        int ny = y + dy[d];
        if (is_blank(nx, ny)) {
            x = nx; y = ny;
        }
        visited[x][y] = true;
    }
    return {x,y};
}

bool check_sequence(const string& seq) {
    // Check palindrome
    int len = seq.size();
    for (int i=0; i<len/2; i++) {
        if (seq[i] != seq[len-1-i]) return false;
    }
    // Simulate
    vector<vector<bool>> visited(n, vector<bool>(m, false));
    auto [fx, fy] = simulate(sr, sc, seq, visited);
    if (fx != er || fy != ec) return false;
    // Check all blank cells visited
    for (int i=0; i<n; i++) {
        for (int j=0; j<m; j++) {
            if (grid[i][j] == '1' && !visited[i][j]) return false;
        }
    }
    return true;
}

// Try to find a palindrome sequence by brute force for small cases
string brute_force() {
    // Only try if total blank cells <= 8
    if (total_blank > 8) return "";
    // IDDFS
    for (int len = 0; len <= 20; len++) {
        string seq(len, ' ');
        function<bool(int)> dfs = [&](int pos) {
            if (pos == (len+1)/2) {
                // fill the rest by palindrome
                for (int i=0; i<len/2; i++) {
                    seq[len-1-i] = seq[i];
                }
                if (check_sequence(seq)) return true;
                return false;
            }
            for (int d=0; d<4; d++) {
                seq[pos] = dir[d];
                if (dfs(pos+1)) return true;
            }
            return false;
        };
        if (dfs(0)) return seq;
    }
    return "";
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n >> m;
    grid.resize(n);
    for (int i=0; i<n; i++) {
        cin >> grid[i];
        for (int j=0; j<m; j++) {
            if (grid[i][j] == '1') total_blank++;
        }
    }
    cin >> sr >> sc >> er >> ec;
    sr--; sc--; er--; ec--;

    if (!connected()) {
        cout << "-1\n";
        return 0;
    }

    if (sr == er && sc == ec && total_blank == 1) {
        cout << "\n";
        return 0;
    }

    // Try brute force for small
    string ans = brute_force();
    if (!ans.empty()) {
        cout << ans << "\n";
        return 0;
    }

    // Try shortest path if it is palindrome
    string sp = shortest_path();
    if (!sp.empty() && check_sequence(sp)) {
        cout << sp << "\n";
        return 0;
    }

    // Try construction with blocked moves at exit
    string bp = find_path_blocked_at_exit();
    if (!bp.empty()) {
        // Find a move that is blocked at exit
        char blocked_move = 0;
        for (int d=0; d<4; d++) {
            if (blocked_at(er, ec, d)) {
                blocked_move = dir[d];
                break;
            }
        }
        if (blocked_move) {
            string seq = bp + blocked_move + string(bp.rbegin(), bp.rend());
            if (check_sequence(seq)) {
                cout << seq << "\n";
                return 0;
            }
        }
        // Try without middle move
        string seq2 = bp + string(bp.rbegin(), bp.rend());
        if (check_sequence(seq2)) {
            cout << seq2 << "\n";
            return 0;
        }
    }

    cout << "-1\n";
    return 0;
}