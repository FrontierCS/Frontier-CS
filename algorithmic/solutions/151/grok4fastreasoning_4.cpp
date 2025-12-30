#include <bits/stdc++.h>
using namespace std;

const int MAXN = 70;
int node_id[MAXN][MAXN];
int row_of[4900];
int col_of[4900];
int ccost[MAXN][MAXN];
int di[] = {-1, 1, 0, 0};
int dj[] = {0, 0, -1, 1};

char get_dir(int i1, int j1, int i2, int j2) {
    int ddi = i2 - i1;
    int ddj = j2 - j1;
    if (ddi == -1 && ddj == 0) return 'U';
    if (ddi == 1 && ddj == 0) return 'D';
    if (ddi == 0 && ddj == -1) return 'L';
    if (ddi == 0 && ddj == 1) return 'R';
    assert(false);
    return ' ';
}

char get_opp(char d) {
    if (d == 'U') return 'D';
    if (d == 'D') return 'U';
    if (d == 'L') return 'R';
    if (d == 'R') return 'L';
    return ' ';
}

int main() {
    int N, si, sj;
    cin >> N >> si >> sj;
    vector<string> grid(N);
    for (int i = 0; i < N; i++) {
        cin >> grid[i];
    }
    memset(node_id, -1, sizeof(node_id));
    int R = 0;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (grid[i][j] != '#') {
                node_id[i][j] = R;
                row_of[R] = i;
                col_of[R] = j;
                ccost[i][j] = grid[i][j] - '0';
                R++;
            }
        }
    }
    struct Edge {
        int u, v, w;
        bool operator<(const Edge& o) const { return w < o.w; }
    };
    vector<Edge> edges;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (grid[i][j] == '#') continue;
            int uid = node_id[i][j];
            for (int d = 0; d < 4; d++) {
                int ni = i + di[d];
                int nj = j + dj[d];
                if (ni >= 0 && ni < N && nj >= 0 && nj < N && grid[ni][nj] != '#') {
                    int vid = node_id[ni][nj];
                    if (uid < vid) {
                        int ww = ccost[i][j] + ccost[ni][nj];
                        edges.push_back({uid, vid, ww});
                    }
                }
            }
        }
    }
    sort(edges.begin(), edges.end());
    vector<int> parent(R);
    for (int i = 0; i < R; i++) parent[i] = i;
    function<int(int)> find = [&](int x) -> int {
        return parent[x] == x ? x : parent[x] = find(parent[x]);
    };
    vector<vector<int>> adj(R);
    int num_edges = 0;
    for (auto& e : edges) {
        int pu = find(e.u);
        int pv = find(e.v);
        if (pu != pv) {
            parent[pu] = pv;
            adj[e.u].push_back(e.v);
            adj[e.v].push_back(e.u);
            num_edges++;
            if (num_edges == R - 1) break;
        }
    }
    int sid = node_id[si][sj];
    vector<char> path_moves;
    function<void(int, int)> tree_dfs = [&](int uid, int par) {
        for (int vid : adj[uid]) {
            if (vid == par) continue;
            int ci = row_of[uid], cj = col_of[uid];
            int ni = row_of[vid], nj = col_of[vid];
            char dir = get_dir(ci, cj, ni, nj);
            path_moves.push_back(dir);
            tree_dfs(vid, uid);
            path_moves.push_back(get_opp(dir));
        }
    };
    tree_dfs(sid, -1);
    for (char c : path_moves) {
        cout << c;
    }
    cout << endl;
    return 0;
}