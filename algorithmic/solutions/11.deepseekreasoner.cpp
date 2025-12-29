#include <bits/stdc++.h>
using namespace std;

int n, m;
vector<string> grid;
int sr, sc, er, ec;

const int dr[4] = {-1, 1, 0, 0};
const int dc[4] = {0, 0, -1, 1};
const char dir_char[4] = {'U', 'D', 'L', 'R'};

// Check if all blank cells are reachable from start
bool connected() {
    vector<vector<bool>> vis(n, vector<bool>(m, false));
    queue<pair<int, int>> q;
    q.push({sr, sc});
    vis[sr][sc] = true;
    int count = 0;
    while (!q.empty()) {
        auto [r, c] = q.front(); q.pop();
        if (grid[r][c] == '1') count++;
        for (int d = 0; d < 4; d++) {
            int nr = r + dr[d];
            int nc = c + dc[d];
            if (nr >= 0 && nr < n && nc >= 0 && nc < m && grid[nr][nc] == '1' && !vis[nr][nc]) {
                vis[nr][nc] = true;
                q.push({nr, nc});
            }
        }
    }
    int total_blank = 0;
    for (int i = 0; i < n; i++)
        for (int j = 0; j < m; j++)
            if (grid[i][j] == '1') total_blank++;
    return count == total_blank;
}

// BFS to find a path from (sr,sc) to (tr,tc), returns move sequence
string bfs_path(int sr, int sc, int tr, int tc) {
    vector<vector<int>> parent_dir(n, vector<int>(m, -1));
    vector<vector<bool>> vis(n, vector<bool>(m, false));
    queue<pair<int, int>> q;
    q.push({sr, sc});
    vis[sr][sc] = true;
    while (!q.empty()) {
        auto [r, c] = q.front(); q.pop();
        if (r == tr && c == tc) {
            string path;
            while (r != sr || c != sc) {
                int d = parent_dir[r][c];
                path += dir_char[d];
                r -= dr[d];
                c -= dc[d];
            }
            reverse(path.begin(), path.end());
            return path;
        }
        for (int d = 0; d < 4; d++) {
            int nr = r + dr[d];
            int nc = c + dc[d];
            if (nr >= 0 && nr < n && nc >= 0 && nc < m && grid[nr][nc] == '1' && !vis[nr][nc]) {
                vis[nr][nc] = true;
                parent_dir[nr][nc] = d;
                q.push({nr, nc});
            }
        }
    }
    return ""; // should not happen if connected
}

// BFS to find the nearest unvisited blank cell from (sr,sc)
// Returns the target cell and the move sequence to it.
pair<int, int> bfs_nearest(int sr, int sc, vector<vector<bool>>& visited, string& path) {
    vector<vector<int>> parent_dir(n, vector<int>(m, -1));
    vector<vector<bool>> vis_bfs(n, vector<bool>(m, false));
    queue<pair<int, int>> q;
    q.push({sr, sc});
    vis_bfs[sr][sc] = true;
    while (!q.empty()) {
        auto [r, c] = q.front(); q.pop();
        if (!visited[r][c] && grid[r][c] == '1') {
            // Found an unvisited blank cell
            path.clear();
            int cr = r, cc = c;
            while (cr != sr || cc != sc) {
                int d = parent_dir[cr][cc];
                path += dir_char[d];
                cr -= dr[d];
                cc -= dc[d];
            }
            reverse(path.begin(), path.end());
            return {r, c};
        }
        for (int d = 0; d < 4; d++) {
            int nr = r + dr[d];
            int nc = c + dc[d];
            if (nr >= 0 && nr < n && nc >= 0 && nc < m && grid[nr][nc] == '1' && !vis_bfs[nr][nc]) {
                vis_bfs[nr][nc] = true;
                parent_dir[nr][nc] = d;
                q.push({nr, nc});
            }
        }
    }
    return {-1, -1}; // no unvisited cell
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n >> m;
    grid.resize(n);
    for (int i = 0; i < n; i++) cin >> grid[i];
    cin >> sr >> sc >> er >> ec;
    sr--; sc--; er--; ec--;

    if (!connected()) {
        cout << "-1\n";
        return 0;
    }

    int total_blank = 0;
    for (int i = 0; i < n; i++)
        for (int j = 0; j < m; j++)
            if (grid[i][j] == '1') total_blank++;

    if (total_blank == 1) {
        // start and exit are the same blank cell
        cout << "\n";
        return 0;
    }

    // Build a walk W that visits all blank cells and ends at exit
    vector<vector<bool>> visited(n, vector<bool>(m, false));
    int cur_r = sr, cur_c = sc;
    visited[cur_r][cur_c] = true;
    string W = "";

    while (true) {
        string path;
        auto [tr, tc] = bfs_nearest(cur_r, cur_c, visited, path);
        if (tr == -1) break; // all blank cells visited
        W += path;
        // Follow the path and mark cells as visited
        for (char move : path) {
            int d = 0;
            while (dir_char[d] != move) d++;
            int nr = cur_r + dr[d];
            int nc = cur_c + dc[d];
            if (nr >= 0 && nr < n && nc >= 0 && nc < m && grid[nr][nc] == '1') {
                cur_r = nr;
                cur_c = nc;
            }
            visited[cur_r][cur_c] = true;
        }
    }

    // If not already at exit, go to exit
    if (cur_r != er || cur_c != ec) {
        string path_to_exit = bfs_path(cur_r, cur_c, er, ec);
        W += path_to_exit;
        for (char move : path_to_exit) {
            int d = 0;
            while (dir_char[d] != move) d++;
            int nr = cur_r + dr[d];
            int nc = cur_c + dc[d];
            if (nr >= 0 && nr < n && nc >= 0 && nc < m && grid[nr][nc] == '1') {
                cur_r = nr;
                cur_c = nc;
            }
            visited[cur_r][cur_c] = true;
        }
    }

    // Palindrome sequence is reverse(W) + W
    string S = string(W.rbegin(), W.rend()) + W;
    cout << S << "\n";

    return 0;
}