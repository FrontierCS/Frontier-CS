#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    vector<vector<int>> orig(n, vector<int>(n));
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            cin >> orig[i][j];
        }
    }

    const int dx[4] = {1, -1, 0, 0};
    const int dy[4] = {0, 0, 1, -1};
    auto inside = [&](int x, int y) {
        return 0 <= x && x < n && 0 <= y && y < n;
    };

    // 1. original adjacency graph
    vector<vector<bool>> adj(m + 1, vector<bool>(m + 1, false));
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            int c = orig[i][j];
            for (int d = 0; d < 4; d++) {
                int ni = i + dx[d];
                int nj = j + dy[d];
                int nd;
                if (inside(ni, nj)) nd = orig[ni][nj];
                else nd = 0;
                if (c != nd) {
                    adj[c][nd] = true;
                    adj[nd][c] = true;
                }
            }
        }
    }

    // 2. boundary colors
    vector<bool> is_boundary_color(m + 1, false);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (i == 0 || i == n - 1 || j == 0 || j == n - 1) {
                int c = orig[i][j];
                is_boundary_color[c] = true;
            }
        }
    }

    // 3. cells that can become zero
    vector<vector<bool>> can_be_zero(n, vector<bool>(n, true));
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            int c = orig[i][j];
            if (!is_boundary_color[c]) {
                can_be_zero[i][j] = false;
                for (int d = 0; d < 4; d++) {
                    int ni = i + dx[d];
                    int nj = j + dy[d];
                    if (inside(ni, nj)) {
                        can_be_zero[ni][nj] = false;
                    }
                }
            }
        }
    }

    random_device rd;
    int best_E = -1;
    vector<vector<int>> best_grid;

    const int NUM_TRIALS = 5;
    const int MAX_PASSES = 100;

    for (int trial = 0; trial < NUM_TRIALS; trial++) {
        vector<vector<int>> cur = orig;
        vector<int> cnt_color(m + 1, 0);
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                cnt_color[cur[i][j]]++;
            }
        }

        vector<vector<int>> edge_count(m + 1, vector<int>(m + 1, 0));
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                int c = cur[i][j];
                if (c == 0) continue;
                for (int d = 0; d < 4; d++) {
                    int ni = i + dx[d];
                    int nj = j + dy[d];
                    if (!inside(ni, nj)) continue;
                    int nd = cur[ni][nj];
                    if (nd == 0 || c == nd) continue;
                    edge_count[c][nd]++;
                }
            }
        }
        for (int c = 1; c <= m; c++) {
            for (int d = c + 1; d <= m; d++) {
                int total = edge_count[c][d] + edge_count[d][c];
                total /= 2;
                edge_count[c][d] = total;
                edge_count[d][c] = total;
            }
        }

        mt19937 g(rd() + trial);
        int passes = 0;
        while (passes < MAX_PASSES) {
            passes++;
            vector<pair<int, int>> candidates;
            for (int i = 0; i < n; i++) {
                for (int j = 0; j < n; j++) {
                    if (cur[i][j] > 0 && can_be_zero[i][j]) {
                        candidates.emplace_back(i, j);
                    }
                }
            }
            if (candidates.empty()) break;
            shuffle(candidates.begin(), candidates.end(), g);

            bool changed = false;
            for (auto [i, j] : candidates) {
                int c = cur[i][j];
                if (c == 0) continue;

                // adjacent to zero or boundary?
                bool adj_zero = false;
                if (i == 0 || i == n - 1 || j == 0 || j == n - 1) {
                    adj_zero = true;
                } else {
                    for (int dir = 0; dir < 4; dir++) {
                        int ni = i + dx[dir];
                        int nj = j + dy[dir];
                        if (inside(ni, nj) && cur[ni][nj] == 0) {
                            adj_zero = true;
                            break;
                        }
                    }
                }
                if (!adj_zero) continue;

                // has same-color neighbor?
                bool same_color_neighbor = false;
                for (int dir = 0; dir < 4; dir++) {
                    int ni = i + dx[dir];
                    int nj = j + dy[dir];
                    if (inside(ni, nj) && cur[ni][nj] == c) {
                        same_color_neighbor = true;
                        break;
                    }
                }
                if (!same_color_neighbor) continue;

                // connectivity check
                int start_i = -1, start_j = -1;
                for (int dir = 0; dir < 4; dir++) {
                    int ni = i + dx[dir];
                    int nj = j + dy[dir];
                    if (inside(ni, nj) && cur[ni][nj] == c) {
                        start_i = ni;
                        start_j = nj;
                        break;
                    }
                }
                vector<vector<bool>> vis(n, vector<bool>(n, false));
                queue<pair<int, int>> q;
                q.push({start_i, start_j});
                vis[start_i][start_j] = true;
                int visited_count = 0;
                while (!q.empty()) {
                    auto [x, y] = q.front(); q.pop();
                    visited_count++;
                    for (int dir = 0; dir < 4; dir++) {
                        int nx = x + dx[dir];
                        int ny = y + dy[dir];
                        if (!inside(nx, ny)) continue;
                        if (nx == i && ny == j) continue;
                        if (cur[nx][ny] == c && !vis[nx][ny]) {
                            vis[nx][ny] = true;
                            q.push({nx, ny});
                        }
                    }
                }
                if (visited_count != cnt_color[c] - 1) continue;

                // adjacency preservation
                bool ok = true;
                for (int dir = 0; dir < 4; dir++) {
                    int ni = i + dx[dir];
                    int nj = j + dy[dir];
                    if (!inside(ni, nj)) continue;
                    int d = cur[ni][nj];
                    if (d > 0 && d != c && adj[c][d]) {
                        if (edge_count[c][d] <= 1) {
                            ok = false;
                            break;
                        }
                    }
                }
                if (!ok) continue;

                // remove cell
                cur[i][j] = 0;
                cnt_color[c]--;
                for (int dir = 0; dir < 4; dir++) {
                    int ni = i + dx[dir];
                    int nj = j + dy[dir];
                    if (!inside(ni, nj)) continue;
                    int d = cur[ni][nj];
                    if (d > 0 && d != c) {
                        edge_count[c][d]--;
                        edge_count[d][c]--;
                    }
                }
                changed = true;
            }
            if (!changed) break;
        }

        int E = 0;
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                if (cur[i][j] == 0) E++;
            }
        }
        if (E > best_E) {
            best_E = E;
            best_grid = cur;
        }
    }

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            cout << best_grid[i][j] << (j == n - 1 ? "\n" : " ");
        }
    }

    return 0;
}