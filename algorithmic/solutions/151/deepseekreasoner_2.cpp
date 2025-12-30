#include <bits/stdc++.h>
using namespace std;

const int INF = 1e9;
const int dx[4] = {1, -1, 0, 0};
const int dy[4] = {0, 0, 1, -1};
char dir_char[4] = {'D', 'U', 'R', 'L'};

struct Point {
    int i, j;
    Point() {}
    Point(int i_, int j_) : i(i_), j(j_) {}
    bool operator==(const Point& other) const {
        return i == other.i && j == other.j;
    }
};

// Hopcroft–Karp for bipartite matching
class BipartiteMatching {
public:
    int n_left, n_right;
    vector<vector<int>> adj;
    vector<int> pair_left, pair_right;
    vector<int> dist;

    BipartiteMatching(int L, int R) : n_left(L), n_right(R), adj(L), pair_left(L, -1), pair_right(R, -1), dist(L) {}

    void add_edge(int u, int v) {
        adj[u].push_back(v);
    }

    bool bfs() {
        queue<int> q;
        for (int u = 0; u < n_left; ++u) {
            if (pair_left[u] == -1) {
                dist[u] = 0;
                q.push(u);
            } else {
                dist[u] = INF;
            }
        }
        bool found = false;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                int u2 = pair_right[v];
                if (u2 != -1 && dist[u2] == INF) {
                    dist[u2] = dist[u] + 1;
                    q.push(u2);
                } else if (u2 == -1) {
                    found = true;
                }
            }
        }
        return found;
    }

    bool dfs(int u) {
        for (int v : adj[u]) {
            int u2 = pair_right[v];
            if (u2 == -1 || (dist[u2] == dist[u] + 1 && dfs(u2))) {
                pair_left[u] = v;
                pair_right[v] = u;
                return true;
            }
        }
        dist[u] = INF;
        return false;
    }

    int max_matching() {
        int match = 0;
        while (bfs()) {
            for (int u = 0; u < n_left; ++u) {
                if (pair_left[u] == -1 && dfs(u)) {
                    match++;
                }
            }
        }
        return match;
    }

    // Returns: (left_in_cover, right_in_cover)
    pair<vector<bool>, vector<bool>> min_vertex_cover() {
        vector<bool> left_vis(n_left, false), right_vis(n_right, false);
        queue<int> q;
        // start from unmatched left nodes
        for (int u = 0; u < n_left; ++u) {
            if (pair_left[u] == -1) {
                left_vis[u] = true;
                q.push(u);
            }
        }
        // BFS alternating paths
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (!right_vis[v] && pair_left[u] != v) { // unmatched edge
                    right_vis[v] = true;
                    int w = pair_right[v];
                    if (w != -1 && !left_vis[w]) {
                        left_vis[w] = true;
                        q.push(w);
                    }
                }
            }
        }
        // MVC: left not visited, right visited
        vector<bool> left_in_cover(n_left, false), right_in_cover(n_right, false);
        for (int u = 0; u < n_left; ++u) {
            if (!left_vis[u]) left_in_cover[u] = true;
        }
        for (int v = 0; v < n_right; ++v) {
            if (right_vis[v]) right_in_cover[v] = true;
        }
        return {left_in_cover, right_in_cover};
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int N, si, sj;
    cin >> N >> si >> sj;
    vector<string> grid(N);
    vector<vector<int>> weight(N, vector<int>(N, 0));
    for (int i = 0; i < N; ++i) {
        cin >> grid[i];
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] != '#') {
                weight[i][j] = grid[i][j] - '0';
            }
        }
    }

    // 1. Identify row segments and column segments
    vector<vector<int>> row_seg_id(N, vector<int>(N, -1));
    vector<vector<int>> col_seg_id(N, vector<int>(N, -1));
    int row_seg_cnt = 0;
    for (int i = 0; i < N; ++i) {
        int j = 0;
        while (j < N) {
            if (grid[i][j] != '#') {
                int start = j;
                while (j < N && grid[i][j] != '#') {
                    ++j;
                }
                for (int k = start; k < j; ++k) {
                    row_seg_id[i][k] = row_seg_cnt;
                }
                ++row_seg_cnt;
            } else {
                ++j;
            }
        }
    }
    int col_seg_cnt = 0;
    for (int j = 0; j < N; ++j) {
        int i = 0;
        while (i < N) {
            if (grid[i][j] != '#') {
                int start = i;
                while (i < N && grid[i][j] != '#') {
                    ++i;
                }
                for (int k = start; k < i; ++k) {
                    col_seg_id[k][j] = col_seg_cnt;
                }
                ++col_seg_cnt;
            } else {
                ++i;
            }
        }
    }

    // 2. Build bipartite graph: left = row segments, right = column segments
    BipartiteMatching bm(row_seg_cnt, col_seg_cnt);
    vector<Point> road_points;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] != '#') {
                road_points.emplace_back(i, j);
                int r_id = row_seg_id[i][j];
                int c_id = col_seg_id[i][j];
                bm.add_edge(r_id, c_id);
            }
        }
    }

    // 3. Compute maximum matching and minimum vertex cover
    bm.max_matching();
    auto [left_in_cover, right_in_cover] = bm.min_vertex_cover();

    // 4. Greedy selection of squares to cover all segments in MVC
    vector<bool> need_row(row_seg_cnt, false), need_col(col_seg_cnt, false);
    for (int i = 0; i < row_seg_cnt; ++i) {
        if (left_in_cover[i]) need_row[i] = true;
    }
    for (int i = 0; i < col_seg_cnt; ++i) {
        if (right_in_cover[i]) need_col[i] = true;
    }

    vector<bool> covered_row(row_seg_cnt, false), covered_col(col_seg_cnt, false);
    vector<Point> selected;
    selected.emplace_back(si, sj);
    int start_r = row_seg_id[si][sj];
    int start_c = col_seg_id[si][sj];
    if (need_row[start_r]) covered_row[start_r] = true;
    if (need_col[start_c]) covered_col[start_c] = true;

    // Remove duplicate squares from road_points? Not necessary.

    while (true) {
        int unc_row = 0, unc_col = 0;
        for (int i = 0; i < row_seg_cnt; ++i) if (need_row[i] && !covered_row[i]) ++unc_row;
        for (int i = 0; i < col_seg_cnt; ++i) if (need_col[i] && !covered_col[i]) ++unc_col;
        if (unc_row == 0 && unc_col == 0) break;

        // Find best square
        int best_gain = -1;
        Point best_p;
        for (const Point& p : road_points) {
            int r = row_seg_id[p.i][p.j];
            int c = col_seg_id[p.i][p.j];
            int gain = 0;
            if (need_row[r] && !covered_row[r]) ++gain;
            if (need_col[c] && !covered_col[c]) ++gain;
            if (gain > best_gain) {
                best_gain = gain;
                best_p = p;
            } else if (gain == best_gain) {
                // tie break: lower weight
                if (weight[p.i][p.j] < weight[best_p.i][best_p.j]) {
                    best_p = p;
                }
            }
        }
        if (best_gain <= 0) break; // should not happen
        selected.push_back(best_p);
        int r = row_seg_id[best_p.i][best_p.j];
        int c = col_seg_id[best_p.i][best_p.j];
        if (need_row[r]) covered_row[r] = true;
        if (need_col[c]) covered_col[c] = true;
    }

    // Remove redundant squares (except start)
    for (size_t i = 1; i < selected.size(); ) {
        Point p = selected[i];
        int r = row_seg_id[p.i][p.j];
        int c = col_seg_id[p.i][p.j];
        bool row_still_covered = false;
        bool col_still_covered = false;
        for (size_t j = 0; j < selected.size(); ++j) {
            if (j == i) continue;
            Point q = selected[j];
            if (row_seg_id[q.i][q.j] == r) row_still_covered = true;
            if (col_seg_id[q.i][q.j] == c) col_still_covered = true;
        }
        bool can_remove = true;
        if (need_row[r] && !row_still_covered) can_remove = false;
        if (need_col[c] && !col_still_covered) can_remove = false;
        if (can_remove) {
            selected.erase(selected.begin() + i);
        } else {
            ++i;
        }
    }

    int M = selected.size();
    // 5. Dijkstra from each selected square
    vector<vector<vector<Point>>> prev(M, vector<vector<Point>>(N, vector<Point>(N, Point(-1, -1))));
    vector<vector<int>> dist_mat(M, vector<int>(M, INF));
    for (int s_idx = 0; s_idx < M; ++s_idx) {
        Point src = selected[s_idx];
        vector<vector<int>> dist(N, vector<int>(N, INF));
        priority_queue<pair<int, Point>, vector<pair<int, Point>>, greater<pair<int, Point>>> pq;
        dist[src.i][src.j] = 0;
        pq.push({0, src});
        while (!pq.empty()) {
            auto [d, p] = pq.top(); pq.pop();
            if (d != dist[p.i][p.j]) continue;
            for (int dir = 0; dir < 4; ++dir) {
                int ni = p.i + dx[dir];
                int nj = p.j + dy[dir];
                if (ni < 0 || ni >= N || nj < 0 || nj >= N) continue;
                if (grid[ni][nj] == '#') continue;
                int nd = d + weight[ni][nj];
                if (nd < dist[ni][nj]) {
                    dist[ni][nj] = nd;
                    prev[s_idx][ni][nj] = p;
                    pq.push({nd, Point(ni, nj)});
                }
            }
        }
        // Store distances to other selected squares
        for (int t_idx = 0; t_idx < M; ++t_idx) {
            Point t = selected[t_idx];
            dist_mat[s_idx][t_idx] = dist[t.i][t.j];
        }
    }

    // 6. TSP heuristic (nearest neighbor) starting from start (index 0)
    vector<int> order(M);
    vector<bool> visited(M, false);
    order[0] = 0;
    visited[0] = true;
    int current = 0;
    for (int i = 1; i < M; ++i) {
        int best = -1;
        int best_dist = INF;
        for (int j = 0; j < M; ++j) {
            if (!visited[j] && dist_mat[current][j] < best_dist) {
                best_dist = dist_mat[current][j];
                best = j;
            }
        }
        order[i] = best;
        visited[best] = true;
        current = best;
    }

    // 7. Reconstruct the path
    string route;
    for (int idx = 0; idx < M; ++idx) {
        int from_idx = order[idx];
        int to_idx = order[(idx + 1) % M];
        Point from = selected[from_idx];
        Point to = selected[to_idx];
        // Reconstruct path from 'from' to 'to'
        vector<Point> path;
        Point cur = to;
        while (!(cur.i == from.i && cur.j == from.j)) {
            path.push_back(cur);
            cur = prev[from_idx][cur.i][cur.j];
        }
        path.push_back(from);
        reverse(path.begin(), path.end());
        // Convert to moves
        for (size_t k = 0; k + 1 < path.size(); ++k) {
            Point a = path[k];
            Point b = path[k+1];
            if (b.i == a.i - 1) route += 'U';
            else if (b.i == a.i + 1) route += 'D';
            else if (b.j == a.j - 1) route += 'L';
            else if (b.j == a.j + 1) route += 'R';
        }
    }

    cout << route << endl;
    return 0;
}