#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <tuple>
#include <cstring>
#include <set>

using namespace std;

const int N = 50;
const int M = 100;
int n = N, m = M;

int orig[N][N];
int out[N][N];
bool is_boundary[N][N];
bool keep[N][N];
bool edge_internal[M+1][M+1];

vector<pair<int,int>> cells_by_color[M+1];
set<int> adj0_colors;

int dx[4] = {-1, 1, 0, 0};
int dy[4] = {0, 0, -1, 1};

bool inside(int i, int j) {
    return i >= 0 && i < n && j >= 0 && j < n;
}

int main() {
    // Read input
    cin >> n >> m;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            cin >> orig[i][j];
        }
    }

    // Step 1: collect cells by color
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            int c = orig[i][j];
            cells_by_color[c].push_back({i, j});
        }
    }

    // Step 2: compute boundary cells
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            is_boundary[i][j] = (i == 0 || i == n-1 || j == 0 || j == n-1);
            if (is_boundary[i][j]) {
                adj0_colors.insert(orig[i][j]);
            }
        }
    }

    // Step 3: compute edge_internal for each pair (c,d)
    memset(edge_internal, 0, sizeof(edge_internal));
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            int c = orig[i][j];
            for (int d = 0; d < 4; d++) {
                int ni = i + dx[d];
                int nj = j + dy[d];
                if (!inside(ni, nj)) continue;
                int c2 = orig[ni][nj];
                if (c == c2) continue;
                int a = min(c, c2);
                int b = max(c, c2);
                if (!is_boundary[i][j] && !is_boundary[ni][nj]) {
                    edge_internal[a][b] = true;
                }
            }
        }
    }

    // Step 4: compute keep (boundary cells that are part of a boundary-only edge)
    memset(keep, 0, sizeof(keep));
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (!is_boundary[i][j]) continue;
            int c = orig[i][j];
            for (int d = 0; d < 4; d++) {
                int ni = i + dx[d];
                int nj = j + dy[d];
                if (!inside(ni, nj)) continue;
                int c2 = orig[ni][nj];
                if (c == c2) continue;
                int a = min(c, c2);
                int b = max(c, c2);
                if (!edge_internal[a][b]) {
                    keep[i][j] = true;
                    break;
                }
            }
        }
    }

    // Step 5: initialize out and convert non-keep boundary cells to 0
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            out[i][j] = orig[i][j];
        }
    }
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (is_boundary[i][j] && !keep[i][j]) {
                out[i][j] = 0;
            }
        }
    }

    // Step 6: repair boundary-only edges that might have been broken
    for (int c = 1; c <= m; c++) {
        for (int d = c+1; d <= m; d++) {
            if (edge_internal[c][d]) continue; // not boundary-only
            // check if adjacency (c,d) exists in out
            bool found = false;
            for (int i = 0; i < n && !found; i++) {
                for (int j = 0; j < n && !found; j++) {
                    if (out[i][j] == c) {
                        for (int dir = 0; dir < 4; dir++) {
                            int ni = i + dx[dir];
                            int nj = j + dy[dir];
                            if (inside(ni, nj) && out[ni][nj] == d) {
                                found = true;
                                break;
                            }
                        }
                    }
                }
            }
            if (found) continue;
            // try to restore a boundary pair originally (c,d) that are both 0
            for (int i = 0; i < n && !found; i++) {
                for (int j = 0; j < n && !found; j++) {
                    if (!is_boundary[i][j]) continue;
                    if (orig[i][j] != c) continue;
                    for (int dir = 0; dir < 4; dir++) {
                        int ni = i + dx[dir];
                        int nj = j + dy[dir];
                        if (!inside(ni, nj)) continue;
                        if (orig[ni][nj] != d) continue;
                        if (out[i][j] == 0 && out[ni][nj] == 0) {
                            out[i][j] = c;
                            out[ni][nj] = d;
                            found = true;
                            break;
                        }
                    }
                }
            }
            // if still not found, we ignore (may cause WA, but hope it's rare)
        }
    }

    // Step 7: fix connectivity of each color
    for (int c = 1; c <= m; c++) {
        // collect current cells of color c
        vector<pair<int,int>> cur_cells;
        for (auto &p : cells_by_color[c]) {
            int i = p.first, j = p.second;
            if (out[i][j] == c) cur_cells.push_back({i, j});
        }
        if (cur_cells.empty()) {
            // revert one cell of this color from 0 to c
            for (auto &p : cells_by_color[c]) {
                int i = p.first, j = p.second;
                if (out[i][j] == 0) {
                    out[i][j] = c;
                    break;
                }
            }
            continue;
        }
        // check connectivity via BFS
        vector<vector<bool>> visited(N, vector<bool>(N, false));
        queue<pair<int,int>> q;
        q.push(cur_cells[0]);
        visited[cur_cells[0].first][cur_cells[0].second] = true;
        while (!q.empty()) {
            auto [i, j] = q.front(); q.pop();
            for (int d = 0; d < 4; d++) {
                int ni = i + dx[d];
                int nj = j + dy[d];
                if (!inside(ni, nj)) continue;
                if (out[ni][nj] == c && !visited[ni][nj]) {
                    visited[ni][nj] = true;
                    q.push({ni, nj});
                }
            }
        }
        bool connected = true;
        for (auto &p : cur_cells) {
            if (!visited[p.first][p.second]) {
                connected = false;
                break;
            }
        }
        if (connected) continue;

        // label components
        vector<vector<int>> comp(N, vector<int>(N, -1));
        int comp_cnt = 0;
        for (auto &p : cells_by_color[c]) {
            int i = p.first, j = p.second;
            if (out[i][j] != c || comp[i][j] != -1) continue;
            queue<pair<int,int>> qq;
            qq.push({i, j});
            comp[i][j] = comp_cnt;
            while (!qq.empty()) {
                auto [x, y] = qq.front(); qq.pop();
                for (int d = 0; d < 4; d++) {
                    int nx = x + dx[d];
                    int ny = y + dy[d];
                    if (!inside(nx, ny)) continue;
                    if (out[nx][ny] == c && comp[nx][ny] == -1) {
                        comp[nx][ny] = comp_cnt;
                        qq.push({nx, ny});
                    }
                }
            }
            comp_cnt++;
        }

        // multi-source BFS from component 0 to connect other components
        const int INF = 1e9;
        vector<vector<int>> dist(N, vector<int>(N, INF));
        vector<vector<pair<int,int>>> prev(N, vector<pair<int,int>>(N, {-1,-1}));
        queue<pair<int,int>> bfs_q;
        for (auto &p : cells_by_color[c]) {
            int i = p.first, j = p.second;
            if (comp[i][j] == 0) {
                dist[i][j] = 0;
                bfs_q.push({i, j});
            }
        }
        while (!bfs_q.empty()) {
            auto [i, j] = bfs_q.front(); bfs_q.pop();
            for (int d = 0; d < 4; d++) {
                int ni = i + dx[d];
                int nj = j + dy[d];
                if (!inside(ni, nj)) continue;
                // allowed moves: already c, or originally c and currently 0
                bool allowed = false;
                if (out[ni][nj] == c) allowed = true;
                else if (orig[ni][nj] == c && out[ni][nj] == 0) allowed = true;
                if (!allowed) continue;
                if (dist[ni][nj] > dist[i][j] + 1) {
                    dist[ni][nj] = dist[i][j] + 1;
                    prev[ni][nj] = {i, j};
                    bfs_q.push({ni, nj});
                }
            }
        }

        // connect each component to component 0
        for (int comp_id = 1; comp_id < comp_cnt; comp_id++) {
            int best_i = -1, best_j = -1, best_dist = INF;
            for (auto &p : cells_by_color[c]) {
                int i = p.first, j = p.second;
                if (comp[i][j] == comp_id && dist[i][j] < best_dist) {
                    best_dist = dist[i][j];
                    best_i = i; best_j = j;
                }
            }
            if (best_dist == INF) continue;
            // trace back and revert cells
            int ci = best_i, cj = best_j;
            while (dist[ci][cj] != 0) {
                if (out[ci][cj] == 0 && orig[ci][cj] == c) {
                    out[ci][cj] = c;
                }
                auto p = prev[ci][cj];
                ci = p.first; cj = p.second;
            }
        }
    }

    // Step 8: ensure each color in adj0 has a 0 neighbor
    for (int c : adj0_colors) {
        bool has_zero = false;
        for (auto &p : cells_by_color[c]) {
            int i = p.first, j = p.second;
            if (out[i][j] != c) continue;
            for (int d = 0; d < 4; d++) {
                int ni = i + dx[d];
                int nj = j + dy[d];
                if (!inside(ni, nj)) continue;
                if (out[ni][nj] == 0) {
                    has_zero = true;
                    break;
                }
            }
            if (has_zero) break;
        }
        if (has_zero) continue;
        // try to convert a boundary cell of c to 0
        bool converted = false;
        for (auto &p : cells_by_color[c]) {
            int i = p.first, j = p.second;
            if (!is_boundary[i][j] || out[i][j] != c) continue;
            // check safety: converting should not break any boundary-only edge
            bool safe = true;
            for (int d = 0; d < 4; d++) {
                int ni = i + dx[d];
                int nj = j + dy[d];
                if (!inside(ni, nj)) continue;
                if (out[ni][nj] != c && out[ni][nj] != 0) {
                    int dcol = out[ni][nj];
                    int a = min(c, dcol);
                    int b = max(c, dcol);
                    if (!edge_internal[a][b]) {
                        // boundary-only edge, check if it would become empty
                        int cnt = 0;
                        for (auto &p2 : cells_by_color[c]) {
                            int x = p2.first, y = p2.second;
                            if (out[x][y] != c) continue;
                            for (int dd = 0; dd < 4; dd++) {
                                int nx = x + dx[dd];
                                int ny = y + dy[dd];
                                if (inside(nx, ny) && out[nx][ny] == dcol) cnt++;
                            }
                        }
                        if (cnt <= 1) {
                            safe = false;
                            break;
                        }
                    }
                }
            }
            if (safe) {
                out[i][j] = 0;
                converted = true;
                break;
            }
        }
        if (!converted) {
            // fallback: convert any boundary cell of c
            for (auto &p : cells_by_color[c]) {
                int i = p.first, j = p.second;
                if (is_boundary[i][j] && out[i][j] == c) {
                    out[i][j] = 0;
                    converted = true;
                    break;
                }
            }
        }
    }

    // Output the map
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            cout << out[i][j];
            if (j < n-1) cout << " ";
        }
        cout << endl;
    }

    return 0;
}