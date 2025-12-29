#include <bits/stdc++.h>
using namespace std;

const int MAXN = 30;
const int ATTEMPTS = 500;
const string moves = "LURD";  // order for center move tries
const int dr[4] = {0, -1, 0, 1};  // L, U, R, D (matching moves string)
const int dc[4] = {-1, 0, 1, 0};

int n, m;
string grid[MAXN];
int sr, sc, er, ec;
int blank_count;
bool is_blank[MAXN][MAXN];

bool inbounds(int r, int c) {
    return r >= 0 && r < n && c >= 0 && c < m;
}

// BFS to find shortest path from (r1,c1) to (r2,c2) through blank cells.
// Returns sequence of moves as string, or empty if unreachable.
string bfs_path(int r1, int c1, int r2, int c2) {
    vector<vector<int>> dist(n, vector<int>(m, -1));
    vector<vector<pair<int,int>>> parent(n, vector<pair<int,int>>(m, {-1,-1}));
    vector<vector<char>> dir_from_parent(n, vector<char>(m, ' '));
    queue<pair<int,int>> q;
    dist[r1][c1] = 0;
    q.push({r1, c1});
    while (!q.empty()) {
        auto [r, c] = q.front(); q.pop();
        if (r == r2 && c == c2) break;
        for (int d = 0; d < 4; d++) {
            int nr = r + dr[d];
            int nc = c + dc[d];
            if (inbounds(nr, nc) && is_blank[nr][nc] && dist[nr][nc] == -1) {
                dist[nr][nc] = dist[r][c] + 1;
                parent[nr][nc] = {r, c};
                dir_from_parent[nr][nc] = moves[d];  // moves[d] corresponds to dr[d],dc[d]
                q.push({nr, nc});
            }
        }
    }
    if (dist[r2][c2] == -1) return "";
    // Reconstruct path
    string path;
    int r = r2, c = c2;
    while (!(r == r1 && c == c1)) {
        char dir = dir_from_parent[r][c];
        path += dir;
        auto [pr, pc] = parent[r][c];
        r = pr; c = pc;
    }
    reverse(path.begin(), path.end());
    return path;
}

// Simulate sequence from (r,c), return final position.
pair<int,int> simulate(const string& seq, int r, int c) {
    for (char ch : seq) {
        int d = -1;
        if (ch == 'L') d = 0;
        else if (ch == 'U') d = 1;
        else if (ch == 'R') d = 2;
        else if (ch == 'D') d = 3;
        int nr = r + dr[d];
        int nc = c + dc[d];
        if (inbounds(nr, nc) && is_blank[nr][nc]) {
            r = nr; c = nc;
        }
    }
    return {r, c};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    srand(time(0));

    cin >> n >> m;
    for (int i = 0; i < n; i++) {
        cin >> grid[i];
        for (int j = 0; j < m; j++) {
            if (grid[i][j] == '1') is_blank[i][j] = true;
            else is_blank[i][j] = false;
        }
    }
    cin >> sr >> sc >> er >> ec;
    sr--; sc--; er--; ec--;

    // Count blank cells and check connectivity from start
    blank_count = 0;
    for (int i = 0; i < n; i++)
        for (int j = 0; j < m; j++)
            if (is_blank[i][j]) blank_count++;

    vector<vector<bool>> visited_init(n, vector<bool>(m, false));
    queue<pair<int,int>> q;
    visited_init[sr][sc] = true;
    q.push({sr, sc});
    int reachable_count = 0;
    while (!q.empty()) {
        auto [r, c] = q.front(); q.pop();
        reachable_count++;
        for (int d = 0; d < 4; d++) {
            int nr = r + dr[d];
            int nc = c + dc[d];
            if (inbounds(nr, nc) && is_blank[nr][nc] && !visited_init[nr][nc]) {
                visited_init[nr][nc] = true;
                q.push({nr, nc});
            }
        }
    }
    if (reachable_count != blank_count || !visited_init[er][ec]) {
        cout << "-1\n";
        return 0;
    }

    if (blank_count == 1 && sr == er && sc == ec) {
        cout << "\n";
        return 0;
    }

    for (int attempt = 0; attempt < ATTEMPTS; attempt++) {
        vector<vector<bool>> visited(n, vector<bool>(m, false));
        visited[sr][sc] = true;
        int visited_count = 1;
        int cur_r = sr, cur_c = sc;
        string A;

        // Greedy random walk to visit all blank cells
        while (visited_count < blank_count) {
            // Collect unvisited blank cells
            vector<pair<int,int>> unvisited;
            for (int i = 0; i < n; i++)
                for (int j = 0; j < m; j++)
                    if (is_blank[i][j] && !visited[i][j]) unvisited.push_back({i,j});
            // Randomly select one
            int idx = rand() % unvisited.size();
            int target_r = unvisited[idx].first, target_c = unvisited[idx].second;
            string path = bfs_path(cur_r, cur_c, target_r, target_c);
            if (path.empty()) break; // should not happen
            // Follow path, marking visited cells
            for (char ch : path) {
                int d = -1;
                if (ch == 'L') d = 0;
                else if (ch == 'U') d = 1;
                else if (ch == 'R') d = 2;
                else if (ch == 'D') d = 3;
                int nr = cur_r + dr[d];
                int nc = cur_c + dc[d];
                if (inbounds(nr, nc) && is_blank[nr][nc]) {
                    cur_r = nr; cur_c = nc;
                }
                if (!visited[cur_r][cur_c]) {
                    visited[cur_r][cur_c] = true;
                    visited_count++;
                }
            }
            A += path;
        }
        // Now go to exit if not already there
        if (cur_r != er || cur_c != ec) {
            string path_to_exit = bfs_path(cur_r, cur_c, er, ec);
            if (path_to_exit.empty()) continue; // should not happen
            // Follow path (no need to mark visited, all already visited)
            for (char ch : path_to_exit) {
                int d = -1;
                if (ch == 'L') d = 0;
                else if (ch == 'U') d = 1;
                else if (ch == 'R') d = 2;
                else if (ch == 'D') d = 3;
                int nr = cur_r + dr[d];
                int nc = cur_c + dc[d];
                if (inbounds(nr, nc) && is_blank[nr][nc]) {
                    cur_r = nr; cur_c = nc;
                }
            }
            A += path_to_exit;
        }

        // Test A + reverse(A)
        string revA = A;
        reverse(revA.begin(), revA.end());
        string S = A + revA;
        auto [fr, fc] = simulate(S, sr, sc);
        if (fr == er && fc == ec && S.length() <= 1000000) {
            cout << S << "\n";
            return 0;
        }
        // Test A + c + reverse(A) for each c
        for (char c : moves) {
            S = A + c + revA;
            tie(fr, fc) = simulate(S, sr, sc);
            if (fr == er && fc == ec && S.length() <= 1000000) {
                cout << S << "\n";
                return 0;
            }
        }
    }

    cout << "-1\n";
    return 0;
}