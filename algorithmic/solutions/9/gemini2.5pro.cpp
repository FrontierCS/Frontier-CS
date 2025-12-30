#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

const int MAXN = 1005;

vector<pair<int, int>> adj[MAXN];
int p[MAXN];
int n;

int parent[MAXN];
int depth[MAXN];
int tin[MAXN], tout[MAXN];
int timer;
vector<int> nodes_at_depth[MAXN];
int max_depth;

struct Edge {
    int u, v, id;
};
vector<Edge> edges;
int edge_map[MAXN][MAXN];

void dfs(int v, int p, int d) {
    tin[v] = ++timer;
    parent[v] = p;
    depth[v] = d;
    if (d > max_depth) max_depth = d;
    nodes_at_depth[d].push_back(v);

    for (auto& edge_pair : adj[v]) {
        int to = edge_pair.first;
        if (to != p) {
            dfs(to, v, d + 1);
        }
    }
    tout[v] = ++timer;
}

bool is_in_subtree(int u, int v) {
    if (v == 0) return true;
    if (u == 0) return false;
    return tin[v] <= tin[u] && tout[u] <= tout[v];
}

void apply_operation(const vector<int>& op) {
    vector<pair<int,int>> to_swap;
    for (int edge_id : op) {
        to_swap.push_back({edges[edge_id - 1].u, edges[edge_id - 1].v});
    }
    for(auto swp : to_swap){
        swap(p[swp.first], p[swp.second]);
    }
}

void solve() {
    cin >> n;
    for (int i = 1; i <= n; ++i) {
        cin >> p[i];
        adj[i].clear();
        nodes_at_depth[i-1].clear();
    }
    nodes_at_depth[n].clear();

    edges.clear();
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back({v, i + 1});
        adj[v].push_back({u, i + 1});
        edges.push_back({u, v, i + 1});
        edge_map[u][v] = edge_map[v][u] = i+1;
    }

    timer = 0;
    max_depth = 0;
    dfs(1, 0, 0);

    vector<vector<int>> operations;
    
    while (true) {
        bool changed = false;
        // Bottom-up phase
        for (int d = max_depth; d >= 1; --d) {
            vector<int> current_op;
            vector<bool> matched(n + 1, false);
            for (int u : nodes_at_depth[d]) {
                int target = p[u];
                if (!is_in_subtree(target, u)) {
                    int par = parent[u];
                    if (par != 0 && !matched[u] && !matched[par]) {
                        current_op.push_back(edge_map[u][par]);
                        matched[u] = true;
                        matched[par] = true;
                    }
                }
            }
            if (!current_op.empty()) {
                operations.push_back(current_op);
                apply_operation(current_op);
                changed = true;
            }
        }
        if (!changed) break;
    }
    
    while (true) {
        bool sorted = true;
        for(int i = 1; i <= n; ++i) if(p[i] != i) sorted = false;
        if(sorted) break;

        bool changed = false;
        // Top-down phase
        for (int d = 0; d < max_depth; ++d) {
            vector<int> current_op;
            vector<bool> matched(n + 1, false);
            for (int u : nodes_at_depth[d]) {
                if (p[u] != u) {
                    int target = p[u];
                    int child_on_path = 0;
                    for(auto& edge_pair : adj[u]){
                        int to = edge_pair.first;
                        if(parent[to] == u && is_in_subtree(target, to)){
                            child_on_path = to;
                            break;
                        }
                    }
                    if(child_on_path != 0 && !matched[u] && !matched[child_on_path]){
                         current_op.push_back(edge_map[u][child_on_path]);
                         matched[u] = true;
                         matched[child_on_path] = true;
                    }
                }
            }
            if (!current_op.empty()) {
                operations.push_back(current_op);
                apply_operation(current_op);
                changed = true;
            }
        }
        if(!changed) break;
    }

    cout << operations.size() << endl;
    for (const auto& op : operations) {
        cout << op.size();
        for (int edge_id : op) {
            cout << " " << edge_id;
        }
        cout << endl;
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