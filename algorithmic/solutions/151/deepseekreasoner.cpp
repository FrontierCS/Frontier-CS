#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <algorithm>
#include <cstring>
#include <set>
#include <map>
#include <random>
#include <tuple>
#include <limits>
#include <cassert>
#include <numeric>

using namespace std;

const int INF = 1e9;
const int di[4] = {-1, 1, 0, 0};
const int dj[4] = {0, 0, -1, 1};
const char dir_char[4] = {'U', 'D', 'L', 'R'};

int N;
vector<string> grid;
vector<vector<int>> w;

vector<vector<int>> row_seg_id, col_seg_id;
vector<vector<pair<int,int>>> row_seg_squares, col_seg_squares;

pair<vector<vector<int>>, vector<vector<int>>> dijkstra(int si, int sj) {
    vector<vector<int>> dist(N, vector<int>(N, INF));
    vector<vector<int>> parent(N, vector<int>(N, -1));
    dist[si][sj] = 0;
    using State = tuple<int,int,int>;
    priority_queue<State, vector<State>, greater<State>> pq;
    pq.emplace(0, si, sj);
    while (!pq.empty()) {
        auto [d, i, j] = pq.top(); pq.pop();
        if (d != dist[i][j]) continue;
        for (int dir = 0; dir < 4; ++dir) {
            int ni = i + di[dir];
            int nj = j + dj[dir];
            if (ni < 0 || ni >= N || nj < 0 || nj >= N) continue;
            if (grid[ni][nj] == '#') continue;
            int nd = d + w[ni][nj];
            if (nd < dist[ni][nj]) {
                dist[ni][nj] = nd;
                parent[ni][nj] = dir;
                pq.emplace(nd, ni, nj);
            }
        }
    }
    return {dist, parent};
}

vector<int> hopcroft_karp(int L, int R, const vector<vector<int>>& adj) {
    vector<int> matchL(L, -1), matchR(R, -1);
    vector<int> dist(L);
    auto bfs = [&]() -> bool {
        queue<int> q;
        for (int u = 0; u < L; ++u) {
            if (matchL[u] == -1) {
                dist[u] = 0;
                q.push(u);
            } else {
                dist[u] = -1;
            }
        }
        bool found = false;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                int u2 = matchR[v];
                if (u2 != -1 && dist[u2] == -1) {
                    dist[u2] = dist[u] + 1;
                    q.push(u2);
                } else if (u2 == -1) {
                    found = true;
                }
            }
        }
        return found;
    };
    function<bool(int)> dfs = [&](int u) -> bool {
        for (int v : adj[u]) {
            int u2 = matchR[v];
            if (u2 == -1 || (dist[u2] == dist[u] + 1 && dfs(u2))) {
                matchL[u] = v;
                matchR[v] = u;
                return true;
            }
        }
        dist[u] = -1;
        return false;
    };
    while (bfs()) {
        for (int u = 0; u < L; ++u) {
            if (matchL[u] == -1 && dfs(u)) {}
        }
    }
    return matchL;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N;
    int si, sj;
    cin >> si >> sj;
    grid.resize(N);
    for (int i = 0; i < N; ++i) cin >> grid[i];

    w.assign(N, vector<int>(N, 0));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] != '#') {
                w[i][j] = grid[i][j] - '0';
            }
        }
    }

    // row segmentation
    row_seg_id.assign(N, vector<int>(N, -1));
    int row_seg_cnt = 0;
    row_seg_squares.clear();
    for (int i = 0; i < N; ++i) {
        int j = 0;
        while (j < N) {
            if (grid[i][j] == '#') { ++j; continue; }
            int start_j = j;
            while (j < N && grid[i][j] != '#') {
                row_seg_id[i][j] = row_seg_cnt;
                ++j;
            }
            ++row_seg_cnt;
        }
    }
    row_seg_squares.resize(row_seg_cnt);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] != '#') {
                int id = row_seg_id[i][j];
                row_seg_squares[id].emplace_back(i, j);
            }
        }
    }

    // column segmentation
    col_seg_id.assign(N, vector<int>(N, -1));
    int col_seg_cnt = 0;
    col_seg_squares.clear();
    for (int j = 0; j < N; ++j) {
        int i = 0;
        while (i < N) {
            if (grid[i][j] == '#') { ++i; continue; }
            int start_i = i;
            while (i < N && grid[i][j] != '#') {
                col_seg_id[i][j] = col_seg_cnt;
                ++i;
            }
            ++col_seg_cnt;
        }
    }
    col_seg_squares.resize(col_seg_cnt);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] != '#') {
                int id = col_seg_id[i][j];
                col_seg_squares[id].emplace_back(i, j);
            }
        }
    }

    // build bipartite graph (row_seg vs col_seg)
    set<pair<int,int>> edge_set;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] != '#') {
                int u = row_seg_id[i][j];
                int v = col_seg_id[i][j];
                edge_set.insert({u, v});
            }
        }
    }
    vector<vector<int>> adj(row_seg_cnt);
    for (auto& e : edge_set) {
        adj[e.first].push_back(e.second);
    }

    // maximum matching
    vector<int> matchL = hopcroft_karp(row_seg_cnt, col_seg_cnt, adj);
    vector<int> matchR(col_seg_cnt, -1);
    for (int u = 0; u < row_seg_cnt; ++u) {
        if (matchL[u] != -1) {
            matchR[matchL[u]] = u;
        }
    }

    // minimum edge cover
    set<pair<int,int>> guard_set;
    // matched edges
    for (int u = 0; u < row_seg_cnt; ++u) {
        if (matchL[u] != -1) {
            int v = matchL[u];
            // find a square with row_seg u and col_seg v
            for (auto& sq : row_seg_squares[u]) {
                int i = sq.first, j = sq.second;
                if (col_seg_id[i][j] == v) {
                    guard_set.insert(sq);
                    break;
                }
            }
        }
    }
    // unmatched rows
    for (int u = 0; u < row_seg_cnt; ++u) {
        if (matchL[u] == -1 && !row_seg_squares[u].empty()) {
            guard_set.insert(row_seg_squares[u][0]);
        }
    }
    // unmatched columns (only if not already covered)
    vector<bool> col_covered(col_seg_cnt, false);
    for (auto& sq : guard_set) {
        int v = col_seg_id[sq.first][sq.second];
        col_covered[v] = true;
    }
    for (int v = 0; v < col_seg_cnt; ++v) {
        if (!col_covered[v] && !col_seg_squares[v].empty()) {
            guard_set.insert(col_seg_squares[v][0]);
        }
    }
    // add start
    guard_set.insert({si, sj});

    // convert to vector
    vector<pair<int,int>> guards(guard_set.begin(), guard_set.end());
    int m = guards.size();

    // guard auxiliary data
    vector<int> guard_row_seg(m), guard_col_seg(m);
    vector<int> row_seg_count(row_seg_cnt, 0), col_seg_count(col_seg_cnt, 0);
    vector<vector<int>> guard_index(N, vector<int>(N, -1));
    for (int idx = 0; idx < m; ++idx) {
        int i = guards[idx].first, j = guards[idx].second;
        guard_index[i][j] = idx;
        int r = row_seg_id[i][j];
        int c = col_seg_id[i][j];
        guard_row_seg[idx] = r;
        guard_col_seg[idx] = c;
        row_seg_count[r]++;
        col_seg_count[c]++;
    }

    int start_idx = -1;
    for (int idx = 0; idx < m; ++idx) {
        if (guards[idx].first == si && guards[idx].second == sj) {
            start_idx = idx;
            break;
        }
    }
    assert(start_idx != -1);

    // prune redundant guards (except start)
    random_device rd;
    mt19937 g(rd());
    vector<int> order(m);
    iota(order.begin(), order.end(), 0);
    shuffle(order.begin(), order.end(), g);
    vector<bool> kept(m, true);
    for (int idx : order) {
        if (idx == start_idx) continue;
        if (!kept[idx]) continue;
        int r = guard_row_seg[idx];
        int c = guard_col_seg[idx];
        if (row_seg_count[r] > 1 && col_seg_count[c] > 1) {
            kept[idx] = false;
            row_seg_count[r]--;
            col_seg_count[c]--;
        }
    }
    vector<pair<int,int>> new_guards;
    vector<int> new_guard_row_seg, new_guard_col_seg;
    guard_index.assign(N, vector<int>(N, -1));
    for (int idx = 0; idx < m; ++idx) {
        if (kept[idx]) {
            new_guards.push_back(guards[idx]);
            new_guard_row_seg.push_back(guard_row_seg[idx]);
            new_guard_col_seg.push_back(guard_col_seg[idx]);
            guard_index[guards[idx].first][guards[idx].second] = new_guards.size() - 1;
        }
    }
    guards = move(new_guards);
    guard_row_seg = move(new_guard_row_seg);
    guard_col_seg = move(new_guard_col_seg);
    m = guards.size();
    // update start_idx
    for (int idx = 0; idx < m; ++idx) {
        if (guards[idx].first == si && guards[idx].second == sj) {
            start_idx = idx;
            break;
        }
    }

    // greedy walk
    vector<bool> visited(m, false);
    visited[start_idx] = true;
    pair<int,int> current = {si, sj};
    string total_moves;

    while (true) {
        // collect unvisited guards
        vector<int> targets;
        for (int idx = 0; idx < m; ++idx) {
            if (!visited[idx]) targets.push_back(idx);
        }
        if (targets.empty()) break;

        auto [dist, parent] = dijkstra(current.first, current.second);

        // find nearest unvisited guard
        int best = -1, best_dist = INF;
        for (int idx : targets) {
            int i = guards[idx].first, j = guards[idx].second;
            int d = dist[i][j];
            if (d < best_dist) {
                best_dist = d;
                best = idx;
            }
        }
        if (best == -1) break; // should not happen

        // reconstruct path to best
        vector<int> moves_seq;
        int ci = guards[best].first, cj = guards[best].second;
        while (ci != current.first || cj != current.second) {
            int dir = parent[ci][cj];
            moves_seq.push_back(dir);
            int pi, pj;
            if (dir == 0) { pi = ci - 1; pj = cj; }
            else if (dir == 1) { pi = ci + 1; pj = cj; }
            else if (dir == 2) { pi = ci; pj = cj - 1; }
            else { pi = ci; pj = cj + 1; }
            ci = pi; cj = pj;
        }
        reverse(moves_seq.begin(), moves_seq.end());

        // execute moves
        for (int dir : moves_seq) {
            total_moves += dir_char[dir];
            current.first += di[dir];
            current.second += dj[dir];
            int idx = guard_index[current.first][current.second];
            if (idx != -1 && !visited[idx]) {
                visited[idx] = true;
            }
        }
        // ensure target is marked visited
        if (!visited[best]) {
            visited[best] = true;
        }
    }

    // return to start
    auto [dist, parent] = dijkstra(current.first, current.second);
    vector<int> moves_back;
    int ci = si, cj = sj;
    while (ci != current.first || cj != current.second) {
        int dir = parent[ci][cj];
        moves_back.push_back(dir);
        int pi, pj;
        if (dir == 0) { pi = ci - 1; pj = cj; }
        else if (dir == 1) { pi = ci + 1; pj = cj; }
        else if (dir == 2) { pi = ci; pj = cj - 1; }
        else { pi = ci; pj = cj + 1; }
        ci = pi; cj = pj;
    }
    reverse(moves_back.begin(), moves_back.end());
    for (int dir : moves_back) {
        total_moves += dir_char[dir];
    }

    cout << total_moves << endl;
    return 0;
}