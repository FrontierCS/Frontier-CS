#include <bits/stdc++.h>
using namespace std;
using pii = pair<int, int>;

int main() {
    int N, si, sj;
    cin >> N >> si >> sj;
    vector<string> grid(N);
    for (int i = 0; i < N; i++) cin >> grid[i];
    vector<pii> road_list;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (grid[i][j] != '#') {
                road_list.emplace_back(i, j);
            }
        }
    }
    int R = road_list.size();
    vector<vector<int>> nodeid(N, vector<int>(N, -1));
    for (int idx = 0; idx < R; idx++) {
        auto [i, j] = road_list[idx];
        nodeid[i][j] = idx;
    }
    vector<tuple<int, int, int>> edges;
    for (auto [i, j] : road_list) {
        // down
        int ni = i + 1, nj = j;
        if (ni < N && grid[ni][nj] != '#') {
            int uid = nodeid[i][j];
            int vid = nodeid[ni][nj];
            int cost_u = grid[i][j] - '0';
            int cost_v = grid[ni][nj] - '0';
            int ww = cost_u + cost_v;
            edges.emplace_back(ww, uid, vid);
        }
        // right
        ni = i;
        nj = j + 1;
        if (nj < N && grid[ni][nj] != '#') {
            int uid = nodeid[i][j];
            int vid = nodeid[ni][nj];
            int cost_u = grid[i][j] - '0';
            int cost_v = grid[ni][nj] - '0';
            int ww = cost_u + cost_v;
            edges.emplace_back(ww, uid, vid);
        }
    }
    sort(edges.begin(), edges.end());
    vector<int> uf(R);
    for (int i = 0; i < R; i++) uf[i] = i;
    auto find = [&](auto&& self, int x) -> int {
        return uf[x] == x ? x : uf[x] = self(self, uf[x]);
    };
    vector<vector<int>> tree_adj(R);
    int components = R;
    for (auto [ww, u, v] : edges) {
        int pu = find(find, u);
        int pv = find(find, v);
        if (pu != pv) {
            uf[pu] = pv;
            tree_adj[u].push_back(v);
            tree_adj[v].push_back(u);
            components--;
            if (components == 1) break;
        }
    }
    int start_id = nodeid[si][sj];
    vector<int> par_id(R, -1);
    vector<bool> vvis(R, false);
    queue<int> qq;
    qq.push(start_id);
    vvis[start_id] = true;
    par_id[start_id] = -2;
    while (!qq.empty()) {
        int u = qq.front(); qq.pop();
        for (int vv : tree_adj[u]) {
            if (!vvis[vv]) {
                vvis[vv] = true;
                par_id[vv] = u;
                qq.push(vv);
            }
        }
    }
    vector<vector<int>> children_id(R);
    for (int u = 0; u < R; u++) {
        int p = par_id[u];
        if (p != -2) {
            children_id[p].push_back(u);
        }
    }
    auto dfs = [&](auto&& self, int uid, vector<pii>& tour) -> void {
        tour.push_back(road_list[uid]);
        for (int vid : children_id[uid]) {
            self(self, vid, tour);
            tour.push_back(road_list[uid]);
        }
    };
    vector<pii> tour;
    if (R > 0) {
        dfs(dfs, start_id, tour);
    }
    string ans;
    int dx[4] = {-1, 1, 0, 0};
    int dy[4] = {0, 0, -1, 1};
    char dirs[4] = {'U', 'D', 'L', 'R'};
    for (size_t k = 0; k + 1 < tour.size(); k++) {
        int i1 = tour[k].first, j1 = tour[k].second;
        int i2 = tour[k + 1].first, j2 = tour[k + 1].second;
        int ddi = i2 - i1;
        int ddj = j2 - j1;
        char dir = 0;
        for (int d = 0; d < 4; d++) {
            if (ddi == dx[d] && ddj == dy[d]) {
                dir = dirs[d];
                break;
            }
        }
        assert(dir != 0);
        ans += dir;
    }
    cout << ans << endl;
}