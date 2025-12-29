#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <cstring>
#include <queue>
#include <map>
#include <functional>
#include <ctime>

using namespace std;

const int N = 50;
const int M = 100;
int n, m;

// directions: up, down, left, right
const int dx[4] = {-1, 1, 0, 0};
const int dy[4] = {0, 0, -1, 1};

struct Solver {
    vector<vector<int>> orig;
    bool required_adj[M+1][M+1] = {false};
    vector<vector<int>> best_map;
    int best_E = -1;

    void read_input() {
        cin >> n >> m;
        orig.assign(n, vector<int>(n));
        for (int i = 0; i < n; ++i)
            for (int j = 0; j < n; ++j)
                cin >> orig[i][j];
    }

    void compute_required_adj() {
        // adjacency from original map
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                int c = orig[i][j];
                // boundary -> adjacent to 0
                if (i == 0 || i == n-1 || j == 0 || j == n-1)
                    required_adj[c][0] = required_adj[0][c] = true;
                // neighbors inside grid
                for (int d = 0; d < 4; ++d) {
                    int ni = i + dx[d], nj = j + dy[d];
                    if (ni < 0 || ni >= n || nj < 0 || nj >= n) continue;
                    int c2 = orig[ni][nj];
                    if (c != c2) {
                        required_adj[c][c2] = required_adj[c2][c] = true;
                    }
                }
            }
        }
    }

    // data structures for current map
    vector<vector<int>> cur;
    vector<vector<pair<int,int>>> cells_by_color;
    vector<vector<int>> idx_in_color;
    int edge_count[M+1][M+1] = {0};
    int zero_adj_count[M+1] = {0};
    vector<vector<bool>> is_articulation;

    void recompute_all() {
        // reset
        cells_by_color.assign(M+1, vector<pair<int,int>>());
        idx_in_color.assign(n, vector<int>(n, -1));
        memset(edge_count, 0, sizeof(edge_count));
        memset(zero_adj_count, 0, sizeof(zero_adj_count));
        is_articulation.assign(n, vector<bool>(n, false));

        // cells_by_color and idx_in_color
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                int c = cur[i][j];
                if (c == 0) continue; // we don't track zeros
                idx_in_color[i][j] = cells_by_color[c].size();
                cells_by_color[c].push_back({i, j});
            }
        }

        // edge_count from interior edges
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                int c1 = cur[i][j];
                if (i+1 < n) {
                    int c2 = cur[i+1][j];
                    if (c1 != c2) {
                        int a = min(c1, c2), b = max(c1, c2);
                        edge_count[a][b]++;
                    }
                }
                if (j+1 < n) {
                    int c2 = cur[i][j+1];
                    if (c1 != c2) {
                        int a = min(c1, c2), b = max(c1, c2);
                        edge_count[a][b]++;
                    }
                }
            }
        }
        // boundary edges with 0
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                int c = cur[i][j];
                if (c == 0) continue;
                if (i == 0 || i == n-1 || j == 0 || j == n-1) {
                    edge_count[0][c]++;
                }
            }
        }

        // zero_adj_count
        for (int c = 1; c <= m; ++c) {
            for (auto& p : cells_by_color[c]) {
                int i = p.first, j = p.second;
                bool adj_zero = false;
                if (i == 0 || i == n-1 || j == 0 || j == n-1) adj_zero = true;
                else {
                    for (int d = 0; d < 4; ++d) {
                        int ni = i + dx[d], nj = j + dy[d];
                        if (ni >= 0 && ni < n && nj >= 0 && nj < n && cur[ni][nj] == 0) {
                            adj_zero = true;
                            break;
                        }
                    }
                }
                if (adj_zero) zero_adj_count[c]++;
            }
        }

        // articulation points for each color
        for (int c = 1; c <= m; ++c) {
            int nc = cells_by_color[c].size();
            if (nc <= 1) continue;
            map<pair<int,int>, int> idx_map;
            for (int k = 0; k < nc; ++k) {
                idx_map[cells_by_color[c][k]] = k;
            }
            vector<vector<int>> graph(nc);
            for (int k = 0; k < nc; ++k) {
                int i = cells_by_color[c][k].first, j = cells_by_color[c][k].second;
                for (int d = 0; d < 4; ++d) {
                    int ni = i + dx[d], nj = j + dy[d];
                    auto it = idx_map.find({ni, nj});
                    if (it != idx_map.end()) {
                        graph[k].push_back(it->second);
                    }
                }
            }
            vector<int> disc(nc, -1), low(nc, 0);
            vector<bool> is_art(nc, false);
            int time = 0;
            function<void(int,int)> dfs = [&](int u, int parent) {
                disc[u] = low[u] = ++time;
                int children = 0;
                for (int v : graph[u]) {
                    if (v == parent) continue;
                    if (disc[v] == -1) {
                        children++;
                        dfs(v, u);
                        low[u] = min(low[u], low[v]);
                        if (parent != -1 && low[v] >= disc[u])
                            is_art[u] = true;
                    } else {
                        low[u] = min(low[u], disc[v]);
                    }
                }
                if (parent == -1 && children > 1)
                    is_art[u] = true;
            };
            dfs(0, -1);
            for (int k = 0; k < nc; ++k) {
                if (is_art[k]) {
                    int i = cells_by_color[c][k].first, j = cells_by_color[c][k].second;
                    is_articulation[i][j] = true;
                }
            }
        }
    }

    bool try_remove(int i, int j) {
        int c = cur[i][j];
        if (c == 0) return false;
        if (cells_by_color[c].size() <= 1) return false;
        if (is_articulation[i][j]) return false;

        // condition: on boundary or adjacent to zero
        bool on_boundary = (i == 0 || i == n-1 || j == 0 || j == n-1);
        bool has_zero_neighbor = false;
        for (int d = 0; d < 4; ++d) {
            int ni = i + dx[d], nj = j + dy[d];
            if (ni >= 0 && ni < n && nj >= 0 && nj < n && cur[ni][nj] == 0) {
                has_zero_neighbor = true;
                break;
            }
        }
        if (!on_boundary && !has_zero_neighbor) return false;

        // condition: for each neighbor color d, if required adjacency, must have edge_count > 1
        for (int d = 0; d < 4; ++d) {
            int ni = i + dx[d], nj = j + dy[d];
            if (ni < 0 || ni >= n || nj < 0 || nj >= n) continue;
            int dcol = cur[ni][nj];
            if (dcol == c || dcol == 0) continue;
            if (required_adj[c][dcol] && edge_count[c][dcol] <= 1) {
                return false;
            }
        }

        // condition: adjacency with 0
        if (required_adj[c][0]) {
            if (zero_adj_count[c] == 1) {
                // check if (i,j) is the only cell adjacent to zero
                bool ij_adj_zero = false;
                if (on_boundary) ij_adj_zero = true;
                else {
                    for (int d = 0; d < 4; ++d) {
                        int ni = i + dx[d], nj = j + dy[d];
                        if (ni >= 0 && ni < n && nj >= 0 && nj < n && cur[ni][nj] == 0) {
                            ij_adj_zero = true;
                            break;
                        }
                    }
                }
                if (ij_adj_zero) return false;
            }
        }

        // all conditions satisfied
        return true;
    }

    void remove_cell(int i, int j) {
        int c = cur[i][j];
        // remove from cells_by_color[c]
        int idx = idx_in_color[i][j];
        auto& vec = cells_by_color[c];
        if (idx != (int)vec.size() - 1) {
            swap(vec[idx], vec.back());
            idx_in_color[vec[idx].first][vec[idx].second] = idx;
        }
        vec.pop_back();
        idx_in_color[i][j] = -1;

        // update edge_count
        // remove edges from (i,j) to neighbors
        for (int d = 0; d < 4; ++d) {
            int ni = i + dx[d], nj = j + dy[d];
            if (ni < 0 || ni >= n || nj < 0 || nj >= n) continue;
            int dcol = cur[ni][nj];
            if (dcol == c) continue;
            if (dcol == 0) {
                edge_count[0][c]--;
            } else {
                int a = min(c, dcol), b = max(c, dcol);
                edge_count[a][b]--;
            }
        }
        // boundary edge with 0 if (i,j) was on boundary
        if (i == 0 || i == n-1 || j == 0 || j == n-1) {
            edge_count[0][c]--;
        }

        // set cell to 0
        cur[i][j] = 0;

        // add new edges from 0 to neighbors
        for (int d = 0; d < 4; ++d) {
            int ni = i + dx[d], nj = j + dy[d];
            if (ni < 0 || ni >= n || nj < 0 || nj >= n) continue;
            int dcol = cur[ni][nj];
            if (dcol == 0) continue;
            edge_count[0][dcol]++;
        }

        // update zero_adj_count for affected colors: c and neighbor colors
        // for color c
        zero_adj_count[c] = 0;
        for (auto& p : cells_by_color[c]) {
            int x = p.first, y = p.second;
            bool adj_zero = false;
            if (x == 0 || x == n-1 || y == 0 || y == n-1) adj_zero = true;
            else {
                for (int dd = 0; dd < 4; ++dd) {
                    int nx = x + dx[dd], ny = y + dy[dd];
                    if (nx >= 0 && nx < n && ny >= 0 && ny < n && cur[nx][ny] == 0) {
                        adj_zero = true;
                        break;
                    }
                }
            }
            if (adj_zero) zero_adj_count[c]++;
        }
        // for neighbor colors
        for (int d = 0; d < 4; ++d) {
            int ni = i + dx[d], nj = j + dy[d];
            if (ni < 0 || ni >= n || nj < 0 || nj >= n) continue;
            int dcol = cur[ni][nj];
            if (dcol == 0 || dcol == c) continue;
            zero_adj_count[dcol] = 0;
            for (auto& p : cells_by_color[dcol]) {
                int x = p.first, y = p.second;
                bool adj_zero = false;
                if (x == 0 || x == n-1 || y == 0 || y == n-1) adj_zero = true;
                else {
                    for (int dd = 0; dd < 4; ++dd) {
                        int nx = x + dx[dd], ny = y + dy[dd];
                        if (nx >= 0 && nx < n && ny >= 0 && ny < n && cur[nx][ny] == 0) {
                            adj_zero = true;
                            break;
                        }
                    }
                }
                if (adj_zero) zero_adj_count[dcol]++;
            }
        }

        // recompute articulation points for color c
        // first clear old articulation flags for color c
        for (auto& p : cells_by_color[c]) {
            is_articulation[p.first][p.second] = false;
        }
        int nc = cells_by_color[c].size();
        if (nc >= 2) {
            map<pair<int,int>, int> idx_map;
            for (int k = 0; k < nc; ++k) {
                idx_map[cells_by_color[c][k]] = k;
            }
            vector<vector<int>> graph(nc);
            for (int k = 0; k < nc; ++k) {
                int x = cells_by_color[c][k].first, y = cells_by_color[c][k].second;
                for (int dd = 0; dd < 4; ++dd) {
                    int nx = x + dx[dd], ny = y + dy[dd];
                    auto it = idx_map.find({nx, ny});
                    if (it != idx_map.end()) {
                        graph[k].push_back(it->second);
                    }
                }
            }
            vector<int> disc(nc, -1), low(nc, 0);
            vector<bool> is_art(nc, false);
            int time = 0;
            function<void(int,int)> dfs = [&](int u, int parent) {
                disc[u] = low[u] = ++time;
                int children = 0;
                for (int v : graph[u]) {
                    if (v == parent) continue;
                    if (disc[v] == -1) {
                        children++;
                        dfs(v, u);
                        low[u] = min(low[u], low[v]);
                        if (parent != -1 && low[v] >= disc[u])
                            is_art[u] = true;
                    } else {
                        low[u] = min(low[u], disc[v]);
                    }
                }
                if (parent == -1 && children > 1)
                    is_art[u] = true;
            };
            dfs(0, -1);
            for (int k = 0; k < nc; ++k) {
                if (is_art[k]) {
                    int x = cells_by_color[c][k].first, y = cells_by_color[c][k].second;
                    is_articulation[x][y] = true;
                }
            }
        }
    }

    void solve_iteration(int seed) {
        cur = orig;
        recompute_all();

        mt19937 rng(seed);
        while (true) {
            vector<pair<int,int>> candidates;
            for (int i = 0; i < n; ++i)
                for (int j = 0; j < n; ++j)
                    if (cur[i][j] != 0)
                        candidates.push_back({i, j});
            if (candidates.empty()) break;
            shuffle(candidates.begin(), candidates.end(), rng);
            bool removed = false;
            for (auto& p : candidates) {
                int i = p.first, j = p.second;
                if (try_remove(i, j)) {
                    remove_cell(i, j);
                    removed = true;
                    break;
                }
            }
            if (!removed) break;
        }

        int E = 0;
        for (int i = 0; i < n; ++i)
            for (int j = 0; j < n; ++j)
                if (cur[i][j] == 0)
                    E++;
        if (E > best_E) {
            best_E = E;
            best_map = cur;
        }
    }

    void solve() {
        compute_required_adj();
        best_map = orig;
        best_E = 0;

        const int NUM_ITER = 10;
        for (int iter = 0; iter < NUM_ITER; ++iter) {
            solve_iteration(iter + 12345 * iter);
        }

        // output best_map
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                if (j) cout << " ";
                cout << best_map[i][j];
            }
            cout << endl;
        }
    }
};

int main() {
    Solver solver;
    solver.read_input();
    solver.solve();
    return 0;
}