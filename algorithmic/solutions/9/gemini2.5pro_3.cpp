#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

const int MAXN = 1005;
const int LOGN = 11;

int n;
vector<int> adj[MAXN];
map<pair<int, int>, int> edge_to_idx;

int p[MAXN];
int pos[MAXN];

int depth[MAXN];
int parent[MAXN];
int up[MAXN][LOGN];

void bfs(int root) {
    for (int i = 1; i <= n; ++i) {
        depth[i] = -1;
        parent[i] = 0;
    }
    vector<int> q;
    q.push_back(root);
    depth[root] = 0;
    int head = 0;
    while(head < q.size()){
        int u = q[head++];
        for(int v : adj[u]){
            if(depth[v] == -1){
                depth[v] = depth[u] + 1;
                parent[v] = u;
                q.push_back(v);
            }
        }
    }
}

void build_lca() {
    for (int i = 1; i <= n; ++i) {
        up[i][0] = parent[i];
    }
    for (int j = 1; j < LOGN; ++j) {
        for (int i = 1; i <= n; ++i) {
            up[i][j] = up[up[i][j-1]][j-1];
        }
    }
}

int get_ancestor(int u, int k) {
    for (int i = 0; i < LOGN; ++i) {
        if ((k >> i) & 1) {
            u = up[u][i];
        }
    }
    return u;
}

int lca(int u, int v) {
    if (u == 0 || v == 0) return 0;
    if (depth[u] < depth[v]) swap(u, v);
    u = get_ancestor(u, depth[u] - depth[v]);
    if (u == v) return u;
    for (int i = LOGN - 1; i >= 0; --i) {
        if (up[u][i] != up[v][i]) {
            u = up[u][i];
            v = up[v][i];
        }
    }
    return parent[u];
}

void apply_swaps(const vector<pair<int, int>>& matching) {
    for (auto const& edge : matching) {
        int u = edge.first;
        int v = edge.second;
        
        int val_u = p[u];
        int val_v = p[v];

        swap(p[u], p[v]);
        
        pos[val_u] = v;
        pos[val_v] = u;
    }
}

void solve() {
    cin >> n;

    for (int i = 1; i <= n; ++i) {
        adj[i].clear();
    }
    edge_to_idx.clear();

    for (int i = 1; i <= n; ++i) {
        cin >> p[i];
        pos[p[i]] = i;
    }

    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        if (u > v) swap(u, v);
        adj[u].push_back(v);
        adj[v].push_back(u);
        edge_to_idx[{u, v}] = i + 1;
    }

    bfs(1);
    build_lca();

    int max_depth = 0;
    for (int i = 1; i <= n; ++i) {
        max_depth = max(max_depth, depth[i]);
    }

    vector<vector<int>> operations;

    // Uphill phase
    for (int iter = 0; iter <= max_depth; ++iter) {
        // Odd depth children
        vector<pair<int, int>> matching_odd;
        vector<bool> parent_used(n + 1, false);
        for (int u = 1; u <= n; ++u) {
            if (parent[u] != 0 && depth[u] % 2 != 0) {
                if (parent_used[parent[u]]) continue;
                int k = p[u];
                if (pos[k] != k && lca(pos[k], k) != pos[k]) {
                    matching_odd.push_back({u, parent[u]});
                    parent_used[parent[u]] = true;
                }
            }
        }
        if (!matching_odd.empty()) {
            vector<int> op;
            op.push_back(matching_odd.size());
            for (auto const& edge : matching_odd) {
                int u = edge.first, v = edge.second;
                if (u > v) swap(u,v);
                op.push_back(edge_to_idx.at({u,v}));
            }
            operations.push_back(op);
            apply_swaps(matching_odd);
        }

        // Even depth children
        vector<pair<int, int>> matching_even;
        parent_used.assign(n + 1, false);
        for (int u = 1; u <= n; ++u) {
            if (parent[u] != 0 && depth[u] % 2 == 0) {
                if (parent_used[parent[u]]) continue;
                int k = p[u];
                if (pos[k] != k && lca(pos[k], k) != pos[k]) {
                    matching_even.push_back({u, parent[u]});
                    parent_used[parent[u]] = true;
                }
            }
        }
        if (!matching_even.empty()) {
            vector<int> op;
            op.push_back(matching_even.size());
            for (auto const& edge : matching_even) {
                int u = edge.first, v = edge.second;
                if (u > v) swap(u,v);
                op.push_back(edge_to_idx.at({u,v}));
            }
            operations.push_back(op);
            apply_swaps(matching_even);
        }
    }

    // Downhill phase
    for (int iter = 0; iter <= max_depth; ++iter) {
        // Odd depth parents
        vector<pair<int, int>> matching_odd;
        vector<bool> node_used(n + 1, false);
        for (int u = 1; u <= n; ++u) {
            if (depth[u] % 2 != 0) {
                if (node_used[u]) continue;
                int k = p[u];
                if (pos[k] != k && lca(pos[k], k) == pos[k]) {
                    if (depth[k] - depth[u] <= 0) continue;
                    int child = get_ancestor(k, depth[k] - depth[u] - 1);
                    if (!node_used[child]) {
                        matching_odd.push_back({u, child});
                        node_used[u] = true;
                        node_used[child] = true;
                    }
                }
            }
        }
        if (!matching_odd.empty()) {
            vector<int> op;
            op.push_back(matching_odd.size());
            for (auto const& edge : matching_odd) {
                int u = edge.first, v = edge.second;
                if (u > v) swap(u,v);
                op.push_back(edge_to_idx.at({u,v}));
            }
            operations.push_back(op);
            apply_swaps(matching_odd);
        }

        // Even depth parents
        vector<pair<int, int>> matching_even;
        node_used.assign(n + 1, false);
        for (int u = 1; u <= n; ++u) {
            if (depth[u] % 2 == 0) {
                if (node_used[u]) continue;
                int k = p[u];
                if (pos[k] != k && lca(pos[k], k) == pos[k]) {
                    if (depth[k] - depth[u] <= 0) continue;
                    int child = get_ancestor(k, depth[k] - depth[u] - 1);
                    if (!node_used[child]) {
                        matching_even.push_back({u, child});
                        node_used[u] = true;
                        node_used[child] = true;
                    }
                }
            }
        }
        if (!matching_even.empty()) {
            vector<int> op;
            op.push_back(matching_even.size());
            for (auto const& edge : matching_even) {
                int u = edge.first, v = edge.second;
                if (u > v) swap(u,v);
                op.push_back(edge_to_idx.at({u,v}));
            }
            operations.push_back(op);
            apply_swaps(matching_even);
        }
    }

    cout << operations.size() << "\n";
    for (const auto& op : operations) {
        for (int i = 0; i < op.size(); ++i) {
            cout << op[i] << (i == op.size() - 1 ? "" : " ");
        }
        cout << "\n";
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}