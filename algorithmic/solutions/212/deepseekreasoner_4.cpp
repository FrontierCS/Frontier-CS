#include <bits/stdc++.h>
using namespace std;

const int MAXN = 41;
const int dx[4] = {1, -1, 0, 0};
const int dy[4] = {0, 0, 1, -1};

int n, m, L, R, Sx, Sy, Lq, s;
vector<int> q;
bool required[MAXN][MAXN]; // required cells
bool visited[MAXN][MAXN];
vector<pair<int, int>> path;

// Check if sequence a is a subsequence of b
bool is_subsequence(const vector<int>& a, const vector<int>& b) {
    int i = 0;
    for (int x : b) {
        if (i < a.size() && a[i] == x) i++;
    }
    return i == a.size();
}

// BFS to find a path from start to end avoiding blocked cells
// blocked condition: visited or (required and row in unvisited_rows and not target)
vector<pair<int, int>> bfs(pair<int, int> start, pair<int, int> target, 
                           const bool unvisited_rows[MAXN], int target_row, int target_col) {
    bool block[MAXN][MAXN] = {false};
    for (int i = 1; i <= n; i++)
        for (int j = 1; j <= m; j++)
            block[i][j] = visited[i][j];
    // block required cells of unvisited rows except the target cell
    for (int i = 1; i <= n; i++) {
        if (unvisited_rows[i]) {
            for (int j = L; j <= R; j++) {
                if (i == target_row && j == target_col) continue;
                block[i][j] = true;
            }
        }
    }
    // BFS
    queue<pair<int, int>> q;
    pair<int, int> parent[MAXN][MAXN];
    int dist[MAXN][MAXN];
    memset(dist, -1, sizeof(dist));
    dist[start.first][start.second] = 0;
    q.push(start);
    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        if (x == target.first && y == target.second) {
            // reconstruct path
            vector<pair<int, int>> res;
            while (x != start.first || y != start.second) {
                res.emplace_back(x, y);
                auto p = parent[x][y];
                x = p.first; y = p.second;
            }
            reverse(res.begin(), res.end());
            return res;
        }
        for (int d = 0; d < 4; d++) {
            int nx = x + dx[d], ny = y + dy[d];
            if (nx < 1 || nx > n || ny < 1 || ny > m) continue;
            if (block[nx][ny]) continue;
            if (dist[nx][ny] == -1) {
                dist[nx][ny] = dist[x][y] + 1;
                parent[nx][ny] = {x, y};
                q.push({nx, ny});
            }
        }
    }
    return {}; // no path
}

void solve() {
    cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s;
    q.resize(Lq);
    for (int i = 0; i < Lq; i++) cin >> q[i];
    // Precompute required cells
    for (int i = 1; i <= n; i++)
        for (int j = L; j <= R; j++)
            required[i][j] = true;
    int w = R - L + 1;

    // Case 1: w == 1
    if (w == 1) {
        vector<int> seq1, seq2;
        for (int i = Sx; i >= 1; i--) seq1.push_back(i);
        for (int i = Sx; i <= n; i++) seq2.push_back(i);
        if (is_subsequence(q, seq1)) {
            cout << "YES\n";
            path.clear();
            for (int i = Sx; i >= 1; i--) path.emplace_back(i, L);
            for (int i = Sx+1; i <= n; i++) path.emplace_back(i, L);
            // But careful: if we go down from Sx, we already included Sx, so we need to avoid duplicate.
            // Actually seq1 covers from Sx down to 1. So path is just that.
            // However, if we go down, we need to cover from Sx to n, but we started at Sx.
            // So we need to choose the correct direction.
            // We'll check both sequences and pick the one that works.
            // Actually we should output the path corresponding to the chosen sequence.
            // Let's redo:
            if (is_subsequence(q, seq1)) {
                path.clear();
                for (int i = Sx; i >= 1; i--) path.emplace_back(i, L);
                for (int i = Sx+1; i <= n; i++) path.emplace_back(i, L);
                // But this would duplicate Sx? Actually first loop includes Sx, second loop starts from Sx+1.
                // So it's fine.
            } else if (is_subsequence(q, seq2)) {
                path.clear();
                for (int i = Sx; i <= n; i++) path.emplace_back(i, L);
                for (int i = Sx-1; i >= 1; i--) path.emplace_back(i, L);
            } else {
                cout << "NO\n";
                return;
            }
            cout << path.size() << "\n";
            for (auto [x, y] : path) cout << x << " " << y << "\n";
        } else if (is_subsequence(q, seq2)) {
            cout << "YES\n";
            path.clear();
            for (int i = Sx; i <= n; i++) path.emplace_back(i, L);
            for (int i = Sx-1; i >= 1; i--) path.emplace_back(i, L);
            cout << path.size() << "\n";
            for (auto [x, y] : path) cout << x << " " << y << "\n";
        } else {
            cout << "NO\n";
        }
        return;
    }

    // Case 2: whole grid required (L=1 and R=m)
    if (L == 1 && R == m) {
        if (Sx != 1 && Sx != n) {
            cout << "NO\n";
            return;
        }
        vector<int> inc, dec;
        for (int i = 1; i <= n; i++) inc.push_back(i);
        for (int i = n; i >= 1; i--) dec.push_back(i);
        if (Sx == 1 && !is_subsequence(q, inc)) {
            cout << "NO\n";
            return;
        }
        if (Sx == n && !is_subsequence(q, dec)) {
            cout << "NO\n";
            return;
        }
        cout << "YES\n";
        path.clear();
        if (Sx == 1) {
            for (int i = 1; i <= n; i++) {
                if (i % 2 == 1) {
                    for (int j = 1; j <= m; j++) path.emplace_back(i, j);
                } else {
                    for (int j = m; j >= 1; j--) path.emplace_back(i, j);
                }
            }
        } else { // Sx == n
            for (int i = n; i >= 1; i--) {
                // When starting from row n, the first row (n) should be left-to-right
                if ((n - i) % 2 == 0) {
                    for (int j = 1; j <= m; j++) path.emplace_back(i, j);
                } else {
                    for (int j = m; j >= 1; j--) path.emplace_back(i, j);
                }
            }
        }
        // But the path must start at (Sx, Sy) = (Sx, L) = (Sx,1). Check if the first cell matches.
        // In our generated path, the first cell is (1,1) for Sx=1, or (n,1) for Sx=n. Good.
        cout << path.size() << "\n";
        for (auto [x, y] : path) cout << x << " " << y << "\n";
        return;
    }

    // Case 3: general case with buffer columns
    // Check condition: if Sx is in q, then q[0] must be Sx
    bool sx_in_q = false;
    for (int x : q) if (x == Sx) { sx_in_q = true; break; }
    if (sx_in_q && q[0] != Sx) {
        cout << "NO\n";
        return;
    }

    // Construct permutation p
    vector<int> p;
    vector<bool> used(n+1, false);
    p.push_back(Sx);
    used[Sx] = true;
    for (int x : q) {
        if (!used[x]) {
            p.push_back(x);
            used[x] = true;
        }
    }
    for (int i = 1; i <= n; i++) {
        if (!used[i]) p.push_back(i);
    }

    // Simulate path
    memset(visited, 0, sizeof(visited));
    path.clear();
    // Start at (Sx, Sy) = (Sx, L)
    path.emplace_back(Sx, L);
    visited[Sx][L] = true;
    // First row subtour
    int cur_x = Sx, cur_y = L;
    // row p[0] (index 0) is odd? We consider 1-indexed positions: position i (1-based) odd -> start L, even -> start R.
    // For i=1 (first row), odd, so we go from L to R.
    for (int y = L+1; y <= R; y++) {
        path.emplace_back(Sx, y);
        visited[Sx][y] = true;
        cur_y = y;
    }
    // Now iterate over remaining rows
    for (int idx = 1; idx < n; idx++) {
        int row = p[idx];
        int pos = idx + 1; // 1-based position in p
        int entry_col = (pos % 2 == 1) ? L : R;
        int prev_row = p[idx-1];
        int prev_pos = idx; // 1-based
        int prev_exit_col = (prev_pos % 2 == 1) ? R : L;

        // Connection from (prev_row