#include <bits/stdc++.h>
using namespace std;

const int H = 10;
const int INF = 1e9;

class UnionFind {
    vector<int> parent, rank;
public:
    UnionFind(int n) {
        parent.resize(n);
        rank.resize(n, 0);
        for (int i = 0; i < n; ++i) parent[i] = i;
    }
    int find(int x) {
        if (parent[x] != x) parent[x] = find(parent[x]);
        return parent[x];
    }
    bool unite(int x, int y) {
        int rx = find(x), ry = find(y);
        if (rx == ry) return false;
        if (rank[rx] < rank[ry]) parent[rx] = ry;
        else if (rank[rx] > rank[ry]) parent[ry] = rx;
        else { parent[ry] = rx; rank[rx]++; }
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M, H_input;
    cin >> N >> M >> H_input; // H_input is always 10
    vector<int> A(N);
    for (int i = 0; i < N; ++i) cin >> A[i];
    vector<pair<int,int>> edges(M);
    for (int i = 0; i < M; ++i) {
        cin >> edges[i].first >> edges[i].second;
    }
    // read coordinates (not used)
    for (int i = 0; i < N; ++i) {
        int x, y;
        cin >> x >> y;
    }

    const int NUM_ITER = 200; // number of random spanning trees to try
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    int best_score = -1;
    vector<int> best_parent(N, -2);

    for (int iter = 0; iter < NUM_ITER; ++iter) {
        // generate random weights for edges
        vector<int> weight(M);
        for (int i = 0; i < M; ++i) weight[i] = rng();
        vector<int> order(M);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int i, int j) { return weight[i] < weight[j]; });

        // Kruskal to get spanning tree
        UnionFind uf(N);
        vector<pair<int,int>> tree_edges;
        for (int i : order) {
            int u = edges[i].first, v = edges[i].second;
            if (uf.unite(u, v)) {
                tree_edges.emplace_back(u, v);
                if (tree_edges.size() == N-1) break;
            }
        }

        // build adjacency list of the tree
        vector<vector<int>> tree_adj(N);
        for (auto& e : tree_edges) {
            tree_adj[e.first].push_back(e.second);
            tree_adj[e.second].push_back(e.first);
        }

        // --- preprocessing for the tree ---
        vector<vector<int>> neigh(N);
        vector<vector<int>> neigh_idx(N, vector<int>(N, -1));
        for (int v = 0; v < N; ++v) {
            for (int j = 0; j < (int)tree_adj[v].size(); ++j) {
                int u = tree_adj[v][j];
                neigh[v].push_back(u);
                neigh_idx[v][u] = j;
            }
        }

        // root the tree at 0
        vector<int> parent(N, -1);
        vector<vector<int>> children(N);
        function<void(int,int)> dfs_build = [&](int v, int p) {
            parent[v] = p;
            for (int u : tree_adj[v]) {
                if (u == p) continue;
                children[v].push_back(u);
                dfs_build(u, v);
            }
        };
        dfs_build(0, -1);

        // dp_down[v][d] : max total in subtree of v when v has depth d (0<=d<=H)
        vector<vector<int>> dp_down(N, vector<int>(H+1, 0));
        function<void(int)> dfs_dp = [&](int v) {
            for (int u : children[v]) dfs_dp(u);
            for (int d = 0; d <= H; ++d) {
                int val = A[v] * d;
                for (int u : children[v]) {
                    int best_u = dp_down[u][0]; // detach
                    if (d+1 <= H) best_u = max(best_u, dp_down[u][d+1]); // attach
                    val += best_u;
                }
                dp_down[v][d] = val;
            }
        };
        dfs_dp(0);

        // f[v][i][d] : for edge v -> neigh[v][i], max total in the component containing neigh[v][i]
        // when neigh[v][i] has depth d and its parent is v.
        vector<vector<vector<int>>> f(N);
        for (int v = 0; v < N; ++v) {
            f[v].resize(neigh[v].size(), vector<int>(H+1, 0));
        }

        // fill f for downward edges (parent->child)
        function<void(int,int)> dfs_f_down = [&](int v, int p) {
            for (int u : children[v]) {
                int idx = neigh_idx[v][u];
                f[v][idx] = dp_down[u];
                dfs_f_down(u, v);
            }
        };
        dfs_f_down(0, -1);

        // compute f for upward edges (child->parent) using rerooting
        function<void(int,int)> dfs_f_up = [&](int v, int p) {
            // compute S[v][d] : sum over neighbors u of best_from_u(v,d)
            vector<int> S(H+1, 0);
            for (int i = 0; i < (int)neigh[v].size(); ++i) {
                int u = neigh[v][i];
                vector<int>& fvu = f[v][i];
                for (int d = 0; d <= H; ++d) {
                    int best = fvu[0];
                    if (d+1 <= H) best = max(best, fvu[d+1]);
                    S[d] += best;
                }
            }
            // for each child u, compute f[u->v] and store
            for (int u : children[v]) {
                int idx_vu = neigh_idx[v][u];
                vector<int>& fvu = f[v][idx_vu];
                vector<int> best_from_u(H+1);
                for (int d = 0; d <= H; ++d) {
                    best_from_u[d] = fvu[0];
                    if (d+1 <= H) best_from_u[d] = max(best_from_u[d], fvu[d+1]);
                }
                vector<int> f_uv(H+1);
                for (int d = 0; d <= H; ++d) {
                    f_uv[d] = A[v] * d + (S[d] - best_from_u[d]);
                }
                int idx_uv = neigh_idx[u][v];
                f[u][idx_uv] = f_uv;
                dfs_f_up(u, v);
            }
        };
        dfs_f_up(0, -1);

        // compute total[v] = best total when v is root (depth 0)
        vector<int> total(N, 0);
        for (int v = 0; v < N; ++v) {
            for (int i = 0; i < (int)neigh[v].size(); ++i) {
                total[v] += max(f[v][i][1], f[v][i][0]);
            }
        }

        // find best root
        int best_root = 0;
        for (int v = 1; v < N; ++v) {
            if (total[v] > total[best_root]) best_root = v;
        }
        int score = total[best_root]; // sum depth * A

        if (score > best_score) {
            best_score = score;
            // reconstruct forest from best_root
            vector<int> cur_parent(N, -2);
            function<void(int,int,int)> assign = [&](int v, int p, int d) {
                cur_parent[v] = p;
                for (int u : neigh[v]) {
                    if (u == p) continue;
                    if (cur_parent[u] != -2) continue; // already assigned
                    int idx = neigh_idx[v][u];
                    int val_attach = (d+1 <= H) ? f[v][idx][d+1] : -INF;
                    int val_detach = f[v][idx][0];
                    if (val_attach >= val_detach) {
                        assign(u, v, d+1);
                    } else {
                        assign(u, -1, 0);
                    }
                }
            };
            cur_parent[best_root] = -1;
            assign(best_root, -1, 0);
            best_parent = cur_parent;
        }
    }

    // output
    for (int i = 0; i < N; ++i) {
        cout << best_parent[i];
        if (i+1 < N) cout << ' ';
    }
    cout << endl;

    return 0;
}