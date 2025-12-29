#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    int grid[50][50];
    vector<pair<int, int>> cells[101];
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            cin >> grid[i][j];
            cells[grid[i][j]].push_back({i, j});
        }
    }
    bool touches0[101] = {false};
    for (int c = 1; c <= m; c++) {
        for (auto p : cells[c]) {
            int i = p.first, j = p.second;
            if (i == 0 || i == n - 1 || j == 0 || j == n - 1) {
                touches0[c] = true;
                break;
            }
        }
    }
    bool is_boundary[101] = {false};
    for (int c = 1; c <= m; c++) {
        is_boundary[c] = touches0[c];
    }
    bool adjmat[101][101] = {false};
    int touch_a_r[101][101], touch_a_c[101][101];
    int touch_b_r[101][101], touch_b_c[101][101];
    memset(touch_a_r, -1, sizeof(touch_a_r));
    int dx[4] = {-1, 0, 1, 0};
    int dy[4] = {0, 1, 0, -1};
    // horizontal
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n - 1; j++) {
            int a = grid[i][j], b = grid[i][j + 1];
            if (a == b || a == 0 || b == 0) continue;
            int aa = min(a, b), bb = max(a, b);
            if (!adjmat[aa][bb]) {
                adjmat[aa][bb] = true;
                int ar, ac, br, bc;
                if (grid[i][j] == aa) {
                    ar = i; ac = j; br = i; bc = j + 1;
                } else {
                    ar = i; ac = j + 1; br = i; bc = j;
                }
                touch_a_r[aa][bb] = ar;
                touch_a_c[aa][bb] = ac;
                touch_b_r[aa][bb] = br;
                touch_b_c[aa][bb] = bc;
            }
        }
    }
    // vertical
    for (int i = 0; i < n - 1; i++) {
        for (int j = 0; j < n; j++) {
            int a = grid[i][j], b = grid[i + 1][j];
            if (a == b || a == 0 || b == 0) continue;
            int aa = min(a, b), bb = max(a, b);
            if (!adjmat[aa][bb]) {
                adjmat[aa][bb] = true;
                int ar, ac, br, bc;
                if (grid[i][j] == aa) {
                    ar = i; ac = j; br = i + 1; bc = j;
                } else {
                    ar = i + 1; ac = j; br = i; bc = j;
                }
                touch_a_r[aa][bb] = ar;
                touch_a_c[aa][bb] = ac;
                touch_b_r[aa][bb] = br;
                touch_b_c[aa][bb] = bc;
            }
        }
    }
    bool cannot_remove[50][50] = {false};
    // protect neighbors of internal
    for (int c = 1; c <= m; c++) {
        if (!is_boundary[c]) {
            for (auto p : cells[c]) {
                int i = p.first, j = p.second;
                for (int d = 0; d < 4; d++) {
                    int ni = i + dx[d], nj = j + dy[d];
                    if (ni >= 0 && ni < n && nj >= 0 && nj < n) {
                        cannot_remove[ni][nj] = true;
                    }
                }
            }
        }
    }
    // protect one boundary cell per boundary ward
    for (int c = 1; c <= m; c++) {
        if (is_boundary[c]) {
            for (auto p : cells[c]) {
                int i = p.first, j = p.second;
                if (i == 0 || i == n - 1 || j == 0 || j == n - 1) {
                    cannot_remove[i][j] = true;
                    break;
                }
            }
        }
    }
    // protect touch cells for boundary-boundary
    for (int a = 1; a <= m; a++) {
        for (int b = a + 1; b <= m; b++) {
            if (adjmat[a][b] && is_boundary[a] && is_boundary[b]) {
                int r1 = touch_a_r[a][b], c1 = touch_a_c[a][b];
                int r2 = touch_b_r[a][b], c2 = touch_b_c[a][b];
                if (r1 != -1) {
                    cannot_remove[r1][c1] = true;
                    cannot_remove[r2][c2] = true;
                }
            }
        }
    }
    // now for each boundary c, connect terminals
    for (int c = 1; c <= m; c++) {
        if (!is_boundary[c]) continue;
        vector<pair<int, int>> terms;
        for (auto p : cells[c]) {
            int i = p.first, j = p.second;
            if (cannot_remove[i][j]) {
                terms.push_back({i, j});
            }
        }
        int k = terms.size();
        if (k == 0) continue;
        // compute term_dist
        vector<vector<int>> term_dist(k, vector<int>(k, -1));
        for (int s = 0; s < k; s++) {
            int si = terms[s].first, sj = terms[s].second;
            vector<vector<int>> dist(n, vector<int>(n, -1));
            vector<vector<pair<int, int>>> parent(n, vector<pair<int, int>>(n, {-1, -1}));
            queue<pair<int, int>> q;
            q.push({si, sj});
            dist[si][sj] = 0;
            while (!q.empty()) {
                auto [x, y] = q.front(); q.pop();
                for (int d = 0; d < 4; d++) {
                    int nx = x + dx[d], ny = y + dy[d];
                    if (nx >= 0 && nx < n && ny >= 0 && ny < n && grid[nx][ny] == c && dist[nx][ny] == -1) {
                        dist[nx][ny] = dist[x][y] + 1;
                        parent[nx][ny] = {x, y};
                        q.push({nx, ny});
                    }
                }
            }
            for (int t = 0; t < k; t++) {
                int ti = terms[t].first, tj = terms[t].second;
                term_dist[s][t] = dist[ti][tj];
            }
        }
        // MST
        struct Edge {
            int u, v, w;
            bool operator<(const Edge& o) const { return w < o.w; }
        };
        vector<Edge> edges;
        for (int i = 0; i < k; i++) {
            for (int j = i + 1; j < k; j++) {
                int dd = term_dist[i][j];
                if (dd != -1) {
                    edges.push_back({i, j, dd});
                }
            }
        }
        sort(edges.begin(), edges.end());
        vector<int> par(k);
        for (int i = 0; i < k; i++) par[i] = i;
        function<int(int)> find = [&](int x) -> int {
            return par[x] == x ? x : par[x] = find(par[x]);
        };
        vector<pair<int, int>> mst_pairs;
        int components = k;
        for (auto e : edges) {
            int pu = find(e.u), pv = find(e.v);
            if (pu != pv) {
                par[pu] = pv;
                mst_pairs.push_back({e.u, e.v});
                components--;
                if (components == 1) break;
            }
        }
        // now add paths
        set<pair<int, int>> kept_cells;
        for (auto tp : terms) kept_cells.insert(tp);
        for (auto [uu, vv] : mst_pairs) {
            // BFS from uu
            int si = terms[uu].first, sj = terms[uu].second;
            vector<vector<int>> dist(n, vector<int>(n, -1));
            vector<vector<pair<int, int>>> parent(n, vector<pair<int, int>>(n, {-1, -1}));
            queue<pair<int, int>> q;
            q.push({si, sj});
            dist[si][sj] = 0;
            while (!q.empty()) {
                auto [x, y] = q.front(); q.pop();
                for (int d = 0; d < 4; d++) {
                    int nx = x + dx[d], ny = y + dy[d];
                    if (nx >= 0 && nx < n && ny >= 0 && ny < n && grid[nx][ny] == c && dist[nx][ny] == -1) {
                        dist[nx][ny] = dist[x][y] + 1;
                        parent[nx][ny] = {x, y};
                        q.push({nx, ny});
                    }
                }
            }
            // path to vv
            int ti = terms[vv].first, tj = terms[vv].second;
            if (dist[ti][tj] == -1) continue;
            vector<pair<int, int>> path;
            pair<int, int> cur = {ti, tj};
            while (true) {
                path.push_back(cur);
                pair<int, int> pre = parent[cur.first][cur.second];
                if (pre.first == -1 && pre.second == -1) break;
                cur = pre;
            }
            for (auto p : path) {
                kept_cells.insert(p);
            }
        }
        // set cannot_remove
        for (auto p : kept_cells) {
            int i = p.first, j = p.second;
            cannot_remove[i][j] = true;
        }
    }
    // now create d
    int d[50][50];
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            d[i][j] = grid[i][j];
        }
    }
    // flood fill to set 0
    vector<vector<bool>> vis(n, vector<bool>(n, false));
    queue<pair<int, int>> qq;
    // initial boundary cells
    // left
    for (int i = 0; i < n; i++) {
        int j = 0;
        int col = grid[i][j];
        if (is_boundary[col] && !cannot_remove[i][j] && d[i][j] != 0) {
            d[i][j] = 0;
            vis[i][j] = true;
            qq.push({i, j});
        }
    }
    // right
    for (int i = 0; i < n; i++) {
        int j = n - 1;
        int col = grid[i][j];
        if (is_boundary[col] && !cannot_remove[i][j] && d[i][j] != 0) {
            d[i][j] = 0;
            vis[i][j] = true;
            qq.push({i, j});
        }
    }
    // top
    for (int j = 0; j < n; j++) {
        int i = 0;
        int col = grid[i][j];
        if (is_boundary[col] && !cannot_remove[i][j] && d[i][j] != 0) {
            d[i][j] = 0;
            vis[i][j] = true;
            qq.push({i, j});
        }
    }
    // bottom
    for (int j = 0; j < n; j++) {
        int i = n - 1;
        int col = grid[i][j];
        if (is_boundary[col] && !cannot_remove[i][j] && d[i][j] != 0) {
            d[i][j] = 0;
            vis[i][j] = true;
            qq.push({i, j});
        }
    }
    while (!qq.empty()) {
        auto [x, y] = qq.front(); qq.pop();
        for (int dd = 0; dd < 4; dd++) {
            int nx = x + dx[dd], ny = y + dy[dd];
            if (nx >= 0 && nx < n && ny >= 0 && ny < n && !vis[nx][ny]) {
                int col = grid[nx][ny];
                if (is_boundary[col] && !cannot_remove[nx][ny] && d[nx][ny] != 0) {
                    d[nx][ny] = 0;
                    vis[nx][ny] = true;
                    qq.push({nx, ny});
                }
            }
        }
    }
    // output
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (j > 0) cout << " ";
            cout << d[i][j];
        }
        cout << endl;
    }
    return 0;
}